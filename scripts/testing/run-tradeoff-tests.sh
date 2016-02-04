#!/bin/bash
#
# build current moses
# loop ...
#   run experiments
#   evaluate experiment, throw away output etc.
#
# Author: David Madl <git@abanbytes.eu>

#                              1: cube pruning,   -s stack_size
MOSES_OPTS="--search-algorithm 1 -s 5000 -v 1"
# MUST have verbosity level 1 for timestamps!      -v verbosity

# obtain paths ($TEST_FRAMEWORK, ...)
. $(dirname $0)/env.sh

# utility functions (path_split, ...)
. $(dirname $0)/utils.sh

build_moses=$(dirname $0)/build-moses.sh
moses_ini_data=$TEST_FRAMEWORK/bricks/scripts/moses-ini-data.py
multeval=$TEST_FRAMEWORK/tools/multeval/multeval.sh

function build_moses_remote() {
  # sets gitrev=3a87b8f, moses=/framework/path/to/moses/bin, descriptor=moses.master.3a87b8f.Release
  eval $("$build_moses" saxnot)
}

# Fill the OS's disk page cache (hopefully creating equal starting conditions)
#
function cache_model_data() {
  ini=$1
  for f in $($moses_ini_data -f $ini); do
    echo >&2 "    Loading $(basename $f) ..."
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

# Tease apart the timestamped hypothesis lines
#
function zip_timestamped_lines() {
  stamped_lines=$1
  test_hyp=$2
  stamps_before=$3
  stamps_sents=$4
  decoding_time=$5

  # get translation (cut the times off): needs Bash for $'\t'
  cut -d $'\t' -f 2- $stamped_lines | awk 'NR>1' > $test_hyp
  # get timestamps for each sentence's arrival time
  cut -d $'\t' -f 1 $stamped_lines > timestamp.sents_all

  head -n 1 timestamp.sents_all > $stamps_before
  awk 'NR>1' timestamp.sents_all > $stamps_sents

  before=$(head -n 1 timestamp.sents_all)
  last=$(tail -n 1 timestamp.sents_all)

  awk "BEGIN { print $last - $before }" > $decoding_time
}

# Obtain the stderr lines relevant for timing
#
function filter_moses_stderr() {
  gawk '/Start loading text phrase table/ ||
        /Created input-output object/ ||
        /took [0-9.]+ seconds/'
}

# Obtain decoding time per sentence
#
function filter_moses_sent_time() {
  # print all except first line (which is 0.0 s empty profiling sentinel line)
  perl -ne '/Translation took ([0-9.]+) seconds total/ && print "$1\n"' | awk 'NR>1'
}

# Splits a language pair en-de into src_lang=en, trg_lang=de
#
function lang_split() {
  eval $(echo $1 | awk 'BEGIN {FS="-"} { print "src_lang=" $1 "; trg_lang=" $2 }')
}

function lowercase() {
  tr '[:upper:]' '[:lower:]'
}

function run_experiment() {
  moses_cmdline="$1"; wd="$2"; corpus="$3"; trg_lang="$4"

  # TODO: run this in docker!
  echo >&2 "  Running moses decoder: $moses_cmdline"
  timestamp > $wd/profile/timestamp.before_moses
  # trick: cat an empty line (~ 20 ms search) first, to obtain decoding start time
  echo > empty
  cat empty $corpus/test.src | $moses_cmdline 2> moses.stderr | timestamp_lines > test.timestamped.hyp
  timestamp > $wd/profile/timestamp.after_moses

  # Separate into hypotheses and timestamps
  zip_timestamped_lines test.timestamped.hyp test.hyp $wd/profile/timestamp.before_decoding $wd/profile/timestamp.sents $wd/profile/total_decoding_time

  # get only moses timestamp debugging lines
  filter_moses_stderr < moses.stderr > $wd/profile/moses.timing.stderr
  # get decoding time per sentence
  filter_moses_sent_time < $wd/profile/moses.timing.stderr > $wd/profile/sent_decoding_times

  # MultEval requires lowercased corpora
  lowercase < test.hyp > test.lc.hyp
  lowercase < $corpus/test.ref > test.lc.ref

  echo >&2 "  Running multeval..."
  $multeval eval --refs test.lc.ref --hyps-baseline test.lc.hyp --meteor.language $trg_lang > $wd/multeval.out
  echo >&2 "  Done."

  # it doesn't cost us much to keep this in full...
  gzip -c test.hyp > $wd/test.hyp.gz

  ln -s $corpus/test.src $wd/test.src
  ln -s $corpus/test.ref $wd/test.ref

  echo $gitrev > $wd/moses.rev
  echo $descriptor > $wd/moses.build
  echo $moses_cmdline > $wd/moses.cmdline
}



build_moses_remote
# sets gitrev=3a87b8f, moses=/framework/path/to/moses/bin, descriptor=moses.master.3a87b8f.Release

wd_base=$TEST_FRAMEWORK/wd/$(date +%Y-%m-%d_%H-%M-%S)
mkdir $wd_base
echo >&2 "experiment wd is $wd_base ..."

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

  # for now, only run a single tuning run version of the experiments
  if [ "$mini" != "moses.1.ini" -a "$mini" != "moses.6.ini" ]; then
    continue
  fi

  echo >&2 "Running experiment $moses_ini ..."

  echo >&2 "  Loading model data into OS page cache..."
  cache_model_data $moses_ini

  for pop_limit in 200 1000; do
    for stack_size in 10 100 500 2000 10000; do
      wd=$wd_base/$setup/$lang_pair/$mini/$pop_limit/$stack_size
      mkdir -p $wd
      mkdir -p $wd/profile

      # run moses experiments and partially parse output, throw away the rest
      moses_cmdline="$moses $MOSES_OPTS --cube-pruning-pop-limit $pop_limit --stack $stack_size -f $moses_ini"

      run_experiment "$moses_cmdline" $wd $corpus $trg_lang
    done
  done
done


# if [ -z ${var+x} ]; then echo "var is unset";



popd > /dev/null  # $tmp
#popd > /dev/null  # $wd_base

# clean up
rm -rf $tmp
