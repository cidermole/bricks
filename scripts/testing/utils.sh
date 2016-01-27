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
