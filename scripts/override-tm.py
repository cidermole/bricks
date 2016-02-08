#!/usr/bin/env python
#
# Override specific source phrases from a "new" phrase table.
# The remaining phrases are scored from "background" phrase table.
# "new" does not add new phrase pairs, except for the source phrases that were present in "background" before.

from __future__ import print_function

import sys

bg, new = [open(f) for f in sys.argv[1:3]]

def src(l):
    return l.rstrip('\n').split(' ||| ')[0]

new_line = new.readline()
new_src = src(new_line)

bg_line = bg.readline()
bg_src = src(bg_line)

run = True
while run:
    # advance to phrase pair, while printing out unseen bg pairs unchanged
    while bg_src != new_src:
        sys.stdout.write(bg_line)
        bg_line = bg.readline()
        if bg_line == '':
            run = False
            break
        bg_src = src(bg_line)

    #
    # replace entire source phrase block, omitting bg pairs unseen in new
    #

    # advance to next source phrase block in bg, do not print
    while bg_src == new_src:
        bg_line = bg.readline()
        if bg_line == '':
            run = False
            break
        bg_src = src(bg_line)

    # print new phrase block
    cur_new_src = new_src
    while new_src == cur_new_src:
        sys.stdout.write(new_line)
        new_line = new.readline()
        if new_line == '':
            break
        new_src = src(new_line)

