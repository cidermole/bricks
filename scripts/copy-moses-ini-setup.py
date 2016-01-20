#!/usr/bin/env python
#
# Copies moses.ini and model files referenced within to a new location,
# producing a modified moses.ini pointing to the files in the new location.
#
# Author: David Madl <git@abanbytes.eu>

# ConfigParser is not suitable to parse moses.ini since it contains lines without key-value pairs (without an equals sign.)
# Homebrew moses.ini "parser" FTW.
#
# note: we could actually generate a shell script with "copy /fs/source/file.bin $target/file.bin" lines
# "copy" being a shell function that users can write to e.g. scp

import sys
import os
import glob
import shutil
import argparse
from collections import Counter


def parseArguments():
    parser = argparse.ArgumentParser(description='Copies a moses.ini file to a new location while ' +
                                                 'also copying the referenced data files.')
    parser.add_argument('-f', '--input', dest='source_moses_ini', help='moses.ini in its original environment', nargs='?', default='/dev/stdin')
    parser.add_argument('-o', '--output', dest='target_moses_ini', help='target path to moses.ini or directory to store moses.ini', nargs='?', default='/dev/stdout')
    parser.add_argument('output_data_path', help='target path to a directory to store data files')
    parser.add_argument('-d', '--dry-run', dest='dryRun', help='do not actually copy data files, just print summary', action='store_true')

    args = parser.parse_args()

    return args


def failMessage(message):
    sys.stderr.write('error: %s\n' % message)
    sys.exit(1)


def assertOrWarnLine(cond, iline, message):
    if not cond:
        sys.stderr.write('warning: parsing moses.ini line %d: %s\n' % (iline + 1, message))
    return cond


def fixPaths(args):
    if not os.path.isfile(args.source_moses_ini):
        failMessage('source_moses_ini %s is not a file.' % args.source_moses_ini)

    if os.path.isdir(args.target_moses_ini):
        # use default file name moses.ini if storing to a directory
        args.target_moses_ini = os.path.join(args.target_moses_ini, 'moses.ini')

    if not os.path.isdir(args.output_data_path):
        failMessage('output_data_path %s is not a directory.' % args.output_data_path)

    return args


class Feature:
    def __init__(self, nameStub, sourceFeaturePath, targetFeaturePath):
        self.nameStub, self.sourceFeaturePath, self.targetFeaturePath = nameStub, sourceFeaturePath, targetFeaturePath

    def __repr__(self):
        return str((self.nameStub, self.sourceFeaturePath, self.targetFeaturePath))

    def copyData(self, dryRun=False):
        """
        Copy the data files from sourceFeaturePath to targetFeaturePath.
        This is convoluted because:
        * path may be a filename prefix
        * path may be a directory
        In fact, it may be necessary to provide feature function specific rules here...
        """
        targetBase = os.path.dirname(self.targetFeaturePath)
        if not dryRun:
            os.makedirs(targetBase)
        else:
            sys.stderr.write('makedirs(%s)\n' % (targetBase))
        if os.path.isdir(self.sourceFeaturePath):
            if not dryRun:
                shutil.copytree(self.sourceFeaturePath, self.targetFeaturePath)
            else:
                sys.stderr.write('copytree(%s, %s)\n' % (self.sourceFeaturePath, self.targetFeaturePath))
        #elif os.path.isfile():
        #    # BUT: maybe the named one is not the only file... we should still glob.
        else:
            if dryRun:
                sys.stderr.write('copy(%s, %s)\n' % (self.sourceFeaturePath + '*', targetBase))
            for file in glob.glob(self.sourceFeaturePath + '*'):
                target = os.path.join(targetBase, os.path.basename(file))
                if not dryRun:
                    shutil.copy(file, target)
                else:
                    sys.stderr.write('  copy(%s, %s)\n' % (file, target))


class MosesIniConverter:
    def __init__(self, mosesIni, targetDataPath):
        self.mosesIni, self.targetDataPath = mosesIni, targetDataPath

        self.pathedFeatures = {}
        self.description_counts = Counter()  # count unnamed moses features
        self.convertedIni = []

    def convertMosesIni(self):
        """Converts moses.ini paths to point to targetDataPath and collects features"""
        featureSection = False

        for iline, line in enumerate(self.mosesIni):
            parseLine = True
            line = line.rstrip()
            if len(line) == 0 or line[0] == '#':
                # empty lines and comments
                parseLine = False

            # detect the [feature] section, activate featureSection
            if line == '[feature]':
                featureSection = True
                parseLine = False
            elif len(line) > 0 and line[0] == '[':
                featureSection = False
                parseLine = False

            parseLine = parseLine and featureSection

            # replicate other lines we don't care about
            if not parseLine:
                self.convertedIni.append(line)
                continue

            self.parseAppendFeatureLine(iline, line)

        return '\n'.join(self.convertedIni)

    def parseAppendFeatureLine(self, iline, line):
        """Parse a feature line, replacing path if present, and append it to convertedIni."""
        parts = line.split(' ')
        nameStub = parts[0]
        assert(len(nameStub) > 0)  # skipping empty lines guarantees this

        try:
            # len(t) > 0 filters out duplicate spaces
            args = dict([tuple(t.split('=')) for t in parts[1:] if len(t) > 0])
        except ValueError:
            assertOrWarnLine(False, iline, 'failed to parse feature line')
            raise

        # automatic naming for features without a name=, just like in moses
        if not 'name' in args:
            c = self.description_counts[nameStub]
            self.description_counts[nameStub] += 1
            args['name'] = nameStub + str(c)

        # this is the unique name for each feature (e.g. LM0)
        featureName = args['name']


        # the actual core reason why we parsed all the stuff
        if 'path' in args:
            sourceFeaturePath = args['path']
            targetFeaturePath = os.path.join(self.targetDataPath, featureName, os.path.basename(args['path']))
            self.pathedFeatures[featureName] = Feature(nameStub, sourceFeaturePath, targetFeaturePath)

            # change path to the new targetDataPath-prefixed version
            args['path'] = targetFeaturePath
            line = '%s %s' % (nameStub, ' '.join(['='.join(t) for t in args.items()]))

        self.convertedIni.append(line)


args = parseArguments()
args = fixPaths(args)

with open(args.source_moses_ini) as fin:
    converter = MosesIniConverter(fin, args.output_data_path)
    result = converter.convertMosesIni()

with open(args.target_moses_ini, 'w') as fo:
    fo.write(result)

# copy the feature data files for features with a given 'path' attribute
for f in converter.pathedFeatures:
    converter.pathedFeatures[f].copyData(args.dryRun)
