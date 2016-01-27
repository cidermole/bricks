#!/bin/bash
#
# Author: David Madl <git@abanbytes.eu>

# obtain paths ($TEST_FRAMEWORK, ...)
. $(dirname $0)/env.sh

# utility functions (path_split, ...)
. $(dirname $0)/utils.sh


# usage: $0 $wd_base
#
# $wd_base == $TEST_FRAMEWORK/wd/$(date +%Y-%m-%d_%H-%M-%S)

wd_base="$1"

# wd=$wd_base/$setup/$lang_pair/$mini/$pop_limit  # (see run-tradeoff-tests.sh)
path_split

for wd in $wd_base/*/*/*/*; do
  path_split $wd $wd_base setup lang_pair mini pop_limit
  # will iterate pop_limits tightly, due to path construction.

  total_decoding_time=$(cat $wd/profile/total_decoding_time)
  echo "$pop_limit;$total_decoding_time"
done

for mini in $wd_base/*/*/*; do
  # redirect stdout to corresponding results file
  exec > $mini/total_decoding_time-vs-pop_limit.txt

  echo "pop_limit;total_decoding_time;"
  for wd in $mini/*; do
    # iterate pop_limits tightly
    path_split $wd $wd_base setup lang_pair mini pop_limit

    total_decoding_time=$(cat $wd/profile/total_decoding_time)
    echo "$pop_limit;$total_decoding_time;"
  done | sort -n | tee $mini/tmp.txt

  pop_limits=$(cut -d ';' -f 1 $mini/tmp.txt | tr "\n" ';')
  total_decoding_times=$(cut -d ';' -f 2 $mini/tmp.txt | tr "\n" ';')

  # one-time pop_limit values (assumed to be the same across all)
  echo "$pop_limits" > $wd_base/pop_limits.txt
  # aggregate file
  echo -n "$setup;$lang_pair;$total_decoding_times" >> $wd_base/decoding_times.txt

  rm $mini/tmp.txt
done
