#!/bin/bash
#
# Usage:
#
# export PATH=$MOSES_HOME/bin:$PATH
# build-pt.sh crp.fr crp.en align prefix  # prefix="/path/to/pt/model"
#
# may pass additional args after $4, e.g. -m model.dmp (document map)

crp1="$1"
crp2="$2"
align="$3"
prefix="$4"
shift; shift; shift; shift

lang1="${crp1##*.}"
lang2="${crp2##*.}"


mtt-build -i -o "${prefix}.$lang1" "$@" < "$crp1" &
proc1=$!
mtt-build -i -o "${prefix}.$lang2" "$@" < "$crp2" &
proc2=$!
symal2mam "${prefix}.${lang1}-${lang2}.mam" < "$align" &
proc3=$!
wait $proc1 $proc2 $proc3

mmlex-build "${prefix}" $lang1 $lang2 -o "${prefix}.${lang1}-${lang2}.lex"

