#!/bin/bash
#
# build current moses
# loop ...
#   run experiments
#   evaluate experiment, throw away output etc.
#
# Author: David Madl <git@abanbytes.eu>

#                              1: cube pruning,     pop limit, -s stack_size
MOSES_OPTS="--search-algorithm 1 --cube-pruning-pop-limit 5000 -s 5000 -v 1"
# MUST have verbosity level 1 for timestamps!                        -v verbosity

# obtain paths ($TEST_FRAMEWORK, ...)
. $(dirname $0)/env.sh

build_moses=$TEST_FRAMEWORK/bricks/scripts/testing/build-moses.sh
moses_ini_data=$TEST_FRAMEWORK/bricks/scripts/moses-ini-data.py
multeval=$TEST_FRAMEWORK/tools/multeval/multeval.sh

# Fill the OS's disk page cache (hopefully creating equal starting conditions)
#
function cache_data() {
  ini=$1
  for f in $($moses_ini_data -f $ini); do
    cat $f > /dev/null
  done
}

# Timestamp each line (for sentence-level profiling and to avoid shutdown costs)
#
function timestamp_lines() {
  # note: a line fed to this is pretty fast (20-30 us)
  # try $ echo -e "\n\n\n\n\n\n\n\n\n" | timestamp_lines
  perl -pne '
    use Time::HiRes (gettimeofday);
    use POSIX qw(strftime);
    ($s,$ms) = gettimeofday();
    $ms = sprintf("%06.0f", $ms);
    print strftime "%s.$ms\t", gmtime($s);
    '
}

function timestamp() {
  # precision note: two of these run about 30 ms apart (shell, forks, exec, ...)
  echo | timestamp_lines
}

# Obtain the stderr lines relevant for timing
#
function filter_moses_stderr() {
  gawk '/Start loading text phrase table/ ||
        /Created input-output object/ ||
        /took [0-9.]+ seconds/'
}

# Split path into variables
#
# Usage: path_split "/home/david/path/to/somewhere" "/home/david" path1 path2 path3
# ... sets path1=path, path2=to, path3=somewhere
#
function path_split() {
  path=$1
  base=$2
  shift; shift

  # cut the base off the front
  path=$(echo $path | sed -e 's#^'$base'/##g')
  # replace / with spaces
  path_parts=$(echo $path | sed -e 's#/# #g')

  # iterate over path parts and (remaining) arguments
  for part in $path_parts; do
    # set shifted varname argument variable
    eval "$1=$part"
    [ $# -eq 0 ] && break
    shift
  done
}

# Splits a language pair en-de into src_lang=en, trg_lang=de
#
function lang_split() {
  eval $(echo $1 | awk 'BEGIN {FS="-"} { print "src_lang=" $1 "; trg_lang=" $2 }')
}

# Compile recent moses
eval $(ssh saxnot "$build_moses")
# sets gitrev=3a87b8f, moses=/framework/path/to/moses/bin, descriptor=moses.master.3a87b8f.Release

wd_base=$TEST_FRAMEWORK/wd/$(date +%Y-%m-%d_%H-%M-%S)
mkdir $wd_base
echo >&2 "experiment wd is $wd_base..."

#pushd $wd_base > /dev/null
tmp=/tmp/run-tradeoff-tests.$$
mkdir $tmp
pushd $tmp > /dev/null


# directory structure set up by copy-mmt-baseline-models.sh:
#
# ${TEST_FRAMEWORK}/models/${setup}/${src_lang}-${trg_lang}
# /moses.${id}.ini
# /corpus/test.src
# /corpus/test.ref
# /... (model files referred to by moses.${id}.ini)

for moses_ini in $TEST_FRAMEWORK/models/*/*/moses.*.ini; do
  path_split $moses_ini $TEST_FRAMEWORK/models setup lang_pair mini
  lang_split $lang_pair
  corpus=$(dirname $moses_ini)/corpus

  wd=$wd_base/$setup/$lang_pair/$mini
  mkdir -p $wd
  mkdir -p $wd/profile

  # page cache the model data (HDD -> RAM)
  cache_data $moses_ini

  # run moses experiments and partially parse output, throw away the rest
  moses_cmdline="$moses $MOSES_OPTS -f $moses_ini"

  # TODO: run this in docker!
  timestamp > $wd/profile/timestamp.before_moses
  # trick: cat an empty line (~ 20 ms search) first, to obtain decoding start time
  echo > empty
  cat empty $corpus/test.src | $moses_cmdline 2> moses.stderr | timestamp_lines > test.timestamped.hyp
  timestamp > $wd/profile/timestamp.after_moses

  # get translation (cut the times off): needs Bash for $'\t'
  cut -d $'\t' -f 2- test.timestamped.hyp | awk 'NR>1' > test.hyp
  # get timestamps for each sentence's arrival time
  cut -d $'\t' -f 1 test.timestamped.hyp > $wd/profile/timestamp.sents_all
  head -n 1 $wd/profile/timestamp.sents_all > $wd/profile/timestamp.before_decoding
  awk 'NR>1' $wd/profile/timestamp.sents_all > $wd/profile/timestamp.sents

  # get only moses timestamp debugging lines
  filter_moses_stderr moses.stderr > $wd/profile/moses.timing.stderr

  # MultEval requires lowercased corpora
  tr '[:upper:]' '[:lower:]' < test.hyp > test.lc.hyp
  tr '[:upper:]' '[:lower:]' < $corpus/test.ref > test.lc.ref

  $multeval eval --refs test.lc.ref --hyps-baseline test.lc.hyp --meteor.language $trg_lang > $wd/multeval.out

  # it doesn't cost us much to keep this in full...
  gzip -c test.hyp > $wd/timestamped-test.hyp.gz

  echo $gitrev > $wd/moses.rev
  echo $descriptor > $wd/moses.build
  echo $moses_cmdline > $wd/moses.cmdline
done


# if [ -z ${var+x} ]; then echo "var is unset";



popd > /dev/null  # $tmp
#popd > /dev/null  # $wd_base
