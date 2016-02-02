#!/usr/bin/env python
#
# Evaluate training sentence selection.
#
# Input file is a list of 1-based line indices, one per line.
# This file contains --nsel lines of selection first, and then the remaining
# line indices afterwards (as produced naturally by ranking).
#
# Line indices refer to a mixture corpus file which has the hidden corpus
# as its first --nsel lines.
#

from __future__ import division, print_function

import sys
import argparse

parser = argparse.ArgumentParser(description='Evaluate training data selection. Expects the entire corpus as a 1-based permutation, with the first nsel lines selected for training.')
parser.add_argument('--nsel', type=int, help='number of sentences that have been selected')
args = parser.parse_args()


# Process selected lines.
tp, fp, fn = 0, 0, 0
tn = 0

for iline, line in enumerate(sys.stdin):
    # parse 1-based line indices
    i = int(line.rstrip()) - 1

    if iline < args.nsel:
        # lines that have been selected
        if i < args.nsel:
            # should it have been selected?
            tp += 1
        else:
            fp += 1
    else:
        # lines that remain (not selected)
        if i < args.nsel:
            # should it have been selected?
            fn += 1
        else:
            # counted just for completeness
            tn += 1

prec, rec = tp / (tp + fp), tp / (tp + fn)
fscore = 2 * prec * rec / (prec + rec)

sys.stderr.write('pseudo-precision pseudo-recall pseudo-f1\n')
print('%.3lf %.3lf %.3lf' % (prec, rec, fscore))
