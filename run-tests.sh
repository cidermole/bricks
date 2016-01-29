#!/bin/bash
#
# options: "-v" to increase verbosity

python2 -m unittest "$@" tests.ConfigOverrideMapping
python2 -m unittest "$@" tests.ConfigMiniPhraseTable
python2 -m unittest "$@" tests.ConfigOutputList
python2 -m unittest "$@" tests.TestEP
