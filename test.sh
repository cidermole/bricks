#!/bin/bash
#
# options: "-v" to increase verbosity

python2 -m unittest "$@" tests.TestStringMethods
python2 -m unittest "$@" tests.OverrideMapping
