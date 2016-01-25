#!/bin/bash
#
# build current moses
# loop ...
#   run experiments
#   evaluate experiment, throw away output etc.
#
# Author: David Madl <git@abanbytes.eu>

#                              1: cube pruning,     pop limit, -s stack_size
MOSES_OPTS="--search-algorithm 1 --cube-pruning-pop-limit 5000 -s 5000"

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

wd=$TEST_FRAMEWORK/wd/$(date +%Y-%m-%d_%H-%M-%S)
mkdir $wd
echo >&2 "experiment wd is $wd..."

#pushd $wd > /dev/null
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

  # page cache the model data (HDD -> RAM)
  cache_data $moses_ini

  # run moses experiments and partially parse output, throw away the rest
  # TODO: run this in docker!
  $moses $MOSES_OPTS -f $moses_ini -i $corpus/test.src > test.hyp

  # MultEval requires lowercased corpora
  tr '[:upper:]' '[:lower:]' < test.hyp > test.lc.hyp
  tr '[:upper:]' '[:lower:]' < $corpus/test.ref > test.lc.ref

  $multeval eval --refs test.lc.ref --hyps-baseline test.lc.hyp --meteor.language $trg_lang > multeval.out

  wd_out=$wd/$setup/$lang_pair/$mini
  mkdir -p $wd_out

  cp multeval.out $wd_out/
  # TODO: write speed results
done


# if [ -z ${var+x} ]; then echo "var is unset";



popd > /dev/null  # $tmp
#popd > /dev/null  # $wd
