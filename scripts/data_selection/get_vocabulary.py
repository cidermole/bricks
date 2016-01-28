#!/usr/bin/env python
#
# Read tokenized corpus file and produce a vocabulary file with word counts,
# sorted by descending word frequency. The most frequent words get the lowest IDs.
#
# Output is giza vocab file compatible, e.g.
#
# 2 the 18990
# 3 , 13434
# 4 . 10240
# ...

import sys
from collections import Counter

vocab = Counter()

for line in sys.stdin:
    vocab.update(line.split(' '))

sorted_entries = sorted(vocab.items(), key=lambda e: e[1], reverse=True)

print('1\tUNK\t0')
for id, (word, count) in enumerate(sorted_entries, start=2):
    print('%d\t%s\t%d' % (id, word, count))
