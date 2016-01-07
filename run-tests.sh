#!/bin/bash
#
# options: "-v" to increase verbosity

python2 -m unittest "$@" tests.ConfigOverrideMapping
python2 -m unittest "$@" tests.ConfigMiniPhraseTable
