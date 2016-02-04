#!/bin/bash
#
# Author: David Madl <git@abanbytes.eu>

# obtain paths ($TEST_FRAMEWORK, ...)
. $(dirname $0)/env.sh

# utility functions (path_split, ...)
. $(dirname $0)/utils.sh

export PYTHONPATH=$(dirname $0)


function parse_multeval() {
  key=$1
  multeval_out=$2
  python -c "import multeval, sys; print(multeval.MultEval.parseOutput(open(sys.argv[1]).read()).$key)" $multeval_out
}

# Flip around the given column index, making it into a row.
#
function csv_flip_col() {
  idx=$1
  cut -d ';' -f $idx | tr "\n" ';'
}


# usage: $0 $wd_base
#
# $wd_base == $TEST_FRAMEWORK/wd/$(date +%Y-%m-%d_%H-%M-%S)

wd_base="$1"

# wd=$wd_base/$setup/$lang_pair/$mini/$pop_limit/$stack_size  # (see run-tradeoff-tests.sh)

rm -f $wd_base/decoding_times.txt

for full_mini in $wd_base/*/*/*; do
  path_split $full_mini $wd_base setup lang_pair mini

  report=$full_mini/total_decoding_time-vs-pop_limit.txt
  # redirect stdout to corresponding report file
  exec > $report

  echo "pop_limit;stack_size;total_decoding_time;bleu;"
  for wd in $full_mini/*/*; do
    # iterate stack_sizes tightly
    [ -d $wd ] || continue  # skip non-directories (report files)

    path_split $wd $wd_base setup lang_pair mini pop_limit stack_size
    #echo >&2 "path_split -> $setup $lang_pair $mini $pop_limit"

    total_decoding_time=$(cat $wd/profile/total_decoding_time)
    bleu=$(parse_multeval bleu $wd/multeval.out)

    echo "$stack_size;$pop_limit;$total_decoding_time;$bleu;"
  done | sort -n | awk -F ";" '{ if($2 == 10) print $0; }' | tee /tmp/tmp.txt

  # here & now only reports pop_limit 100
  stack_sizes=$(csv_flip_col 1 < /tmp/tmp.txt)
  total_decoding_times=$(csv_flip_col 3 < /tmp/tmp.txt)
  bleu_scores=$(csv_flip_col 4 < /tmp/tmp.txt)

  # one-time stack_size values (assumed to be the same across all)
  echo "$stack_sizes" > $wd_base/stack_sizes.txt
  # aggregate file
  echo "$setup;$lang_pair;$mini;${total_decoding_times}${bleu_scores}" >> $wd_base/decoding_times.txt

  #rm /tmp/tmp.txt

  gnuplot -e "
    set term png;
    set output '$full_mini/time_bleu-vs-pop_limit.png';
    set datafile separator ';';
    set key bottom right;
    set xlabel 'pop\_limit';
    set ylabel 'decoding\_time [s]';
    set y2label 'bleu [%]';
    set y2tics;
    set autoscale y2;
    plot '$report' every ::1 using 1:2 with linespoints title 'decoding\_time' axes x1y1, \
         '$report' every ::1 using 1:3 with linespoints title 'bleu' axes x1y2;
  "
done
