#!/usr/bin/env bash

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

# sequence from 0 to nargs-1
function argseq() { seq 0 $(($# - 1)); }

# 0-based index retrieval of arguments, e.g. "index 0 a b c" -> "a"
#
function index() {
  idx=$1;
  # while [ $idx -gt 0 ]; do shift; done
  for (( ; $idx >= 0; idx=$idx-1 )); do shift; done
  echo "$1"
}
