#!/usr/bin/env python
from __future__ import print_function
#
# Converts a POS tagged corpus into a hybrid POS tag / surface form.
#
# Input:  factored format compatible with Moses.
#
# the|DT apple|NN is|VBZ a|DT fleshy|JJ fruit|NN .|.
#
# Output: (freq < 4, or rank-threshold < 5)
#
# the NN is DT JJ NN .

import sys, argparse
from get_vocabulary import parse_vocabulary

def parseArguments():
    parser = argparse.ArgumentParser(description='Converts a POS tagged corpus into a hybrid POS tag / surface form.')
    parser.add_argument('-t', '--rank-threshold', dest='rank_threshold', help='Word rank threshold below which to use POS tags.', type=int, nargs='?', required=True)
    parser.add_argument('vocabulary', help='vocabulary file with word IDs and frequencies, created from training corpus.')
    return parser.parse_args()

args = parseArguments()

with open(args.vocabulary) as fvocab:
    frequency, word2id = parse_vocabulary(fvocab)

for line in sys.stdin:
    words = []
    for word in line.rstrip().split(' '):
        surface, pos = word.split('|')
        if word2id[surface] < args.rank_threshold:
            # more frequent (smaller ID)
            words.append(surface)
        else:
            # less frequent
            words.append(pos)
    print(' '.join(words))
