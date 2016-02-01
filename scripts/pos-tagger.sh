#!/bin/bash
#
# usage:
# export JAVA_HOME=...
# pos-tagger.sh POS_TOOLS_DIR POS_CACHE_DIR en|it tsv|factored in out

# POS taggers for various languages.
#
#
# these functions output either TSV format:
#   we      PRP
#   went    VBD
#   .       .
#
#   we      PRP
#   ...
#
# or moses factored format:
#   we|PRP went|VBD .|.
#   we|PRP ...
#

POS_TOOLS_DIR=$1
POS_CACHE_DIR=$2
lang=$3
output_type=$4

corpus_in=$5
corpus_out=$6

JAVA=$JAVA_HOME/bin/java
SPT=$POS_TOOLS_DIR/stanford-postagger

OPENNLP=$POS_TOOLS_DIR/apache-opennlp/bin/opennlp
OPENNLP_MODEL=$POS_TOOLS_DIR/opennlp-italian-models/models/it/it-pos-maxent.bin


case "$output_type" in
tsv)
  OUTPUT_FORMAT="cat"
  ;;

factored)
  OUTPUT_FORMAT="tsv2factored"
  ;;

*)
  echo >&2 "output_type must be tsv|factored"
  exit 1
  ;;
esac


# just for reference...
# function factored2tsv() {
#   sed 's/ \?\([^ ][^ ]*\)|\([^ ][^ ]*\)/\1\t\2\n/g'
# }

function tsv2factored() {
    sed 's/\t/|/g' | tr '\n' ' ' | sed 's/  /\n/g'
}


function pos_it() {
    $OPENNLP POSTagger $OPENNLP_MODEL | sed 's/ \?\([^ ][^ ]*\)_\([^ ][^ ]*\)/\1\t\2\n/g'
}

function pos_en() {
    $JAVA -mx300m -cp $SPT/stanford-postagger.jar edu.stanford.nlp.tagger.maxent.MaxentTagger -model \
      $SPT/models/english-left3words-distsim.tagger -outputFormat tsv -sentenceDelimiter newline \
      -tokenize false -textFile /dev/stdin
    # NOTE: "-textFile /dev/stdin" works around double newline after sents when reading from stdin
    # (version stanford-postagger-full-2015-04-20)
}


# check corpus hash to see if this corpus has been POS tagged before
#
# (if we keep doing this caching, a common cache dir and common helper functions would be nice)

hash=$(sha1sum $corpus_in | awk '{print $1}')
cached=$POS_CACHE_DIR/$hash
# we did not add $lang here - one corpus has one language.

# do we have a cache directory?
if [ -d "$POS_CACHE_DIR" ]; then
  # do not have cached version? run tagger.
  if [ ! -e "$cached" ]; then
    echo >&2 "No cached POS tagged corpus, running tagger..."
    eval pos_$lang < $corpus_in > $cached
    gzip $cached
    mv ${cached}.gz $cached
  else
    echo >&2 "Found cached POS tagged corpus."
  fi

  # create the requested output format
  zcat $cached | $OUTPUT_FORMAT > $corpus_out
else
  # do not bother caching.
  eval pos_$lang < $corpus_in | $OUTPUT_FORMAT > $corpus_out
fi
