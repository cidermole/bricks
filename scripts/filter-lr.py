#!/usr/bin/env python
from __future__ import print_function

import sys

lr, pt = [open(f) for f in sys.argv[1:3]]

pp = pt.readline().rstrip('\n').split(' ||| ')[0:2]
lpp = ('','')
l = ''

while True:
    # advance to phrase pair, skipping filtered ones
    while lpp != pp:
        l = lr.readline()
        if l == '':
            break
        lpp = l.rstrip('\n').split(' ||| ')[0:2]
    sys.stdout.write(l)
    # read next phrase pair
    p = pt.readline()
    if p == '':
        break
    pp = p.rstrip('\n').split(' ||| ')[0:2]
