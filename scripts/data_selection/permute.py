#!/usr/bin/env python
#
# uses 1-based line indices in perm.txt

import random
import sys
import os


def usage_and_exit(i):
	sys.stderr.write('Usage: %s <perm.txt> <fwd|rev> < input\n' % sys.argv[0])
	sys.stderr.write('if perm.txt is missing, we will create a random permutation.\n')
	sys.stderr.write('Entire input must fit into RAM.\n')
	sys.exit(i)

######################

if len(sys.argv) < 3:
	usage_and_exit(1)

PERM_TXT = sys.argv[1]
DIR = sys.argv[2]

if DIR != 'fwd' and DIR != 'rev':
	usage_and_exit(2)

######################

def write_shuffled(shuffled, write_perm=True):
	# shuffled = [(1, 'b\n'), (0, 'a\n'), (2, 'c\n')]
	fshuf = sys.stdout

	if write_perm:
		with open(PERM_TXT, 'w') as fperm:
			for i, l in shuffled:
				fperm.write('%d\n' % (i + 1))
				fshuf.write(l)
	else:
		for i, l in shuffled:
			fshuf.write(l)

######################

if len(sys.argv) < 2:
	usage_and_exit(1)

PERM_TXT = sys.argv[1]
DIR = sys.argv[2]

if DIR != 'fwd' and DIR != 'rev':
	usage_and_exit(2)

# requires enough RAM here
lines = sys.stdin.readlines()


if os.path.exists(PERM_TXT):
	with open(PERM_TXT, 'r') as fperm:
		perm = [int(l.strip()) for l in fperm]
	# decide fwd | rev
	if DIR == 'fwd':
		#shuffled = [(p-1, lines[p-1]) for p in perm]
		pass
	elif DIR == 'rev':
		tl = sorted([(p-1, i) for i, p in enumerate(perm)])
		perm = [i+1 for p, i in tl]
	else:
		sys.stderr.write('panic: DIR invalid.\n')
		sys.exit(3)

	if len(perm) != len(lines):
		sys.stderr.write('WARNING: using shorter perm of len %d than %d lines.\n' % (len(perm), len(lines)))

	shuffled = [(p-1, lines[p-1]) for p in perm]
	write_shuffled(shuffled, write_perm=False)
else:
	# create and shuffle a permutation
	rnd = random.SystemRandom()
	shuffled = list(enumerate(lines))
	rnd.shuffle(shuffled)
	write_shuffled(shuffled, write_perm=True)


