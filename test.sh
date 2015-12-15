#!/bin/bash
#
# options: "-v" to increase verbosity

python2 -m unittest "$@" tests.OverrideMapping
python2 -m unittest "$@" tests.MiniPhraseTableConfig
