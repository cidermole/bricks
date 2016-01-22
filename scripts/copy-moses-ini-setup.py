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
import logging
from moses_ini import MosesIniParser


def overrides(interface_class):
    def overrider(method):
        assert(method.__name__ in dir(interface_class))
        return method
    return overrider


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
    """
    Representation of single feature line in moses.ini
    """
    def __init__(self, nameStub, uniqueName, sourceDataPath):
        """
        @param nameStub:   PhraseTableMemory
        @param uniqueName: PT0
        @param sourceDataPath: /home/user/models/phrase-table.0-0.1.1.gz
        """
        self.nameStub, self.uniqueName, self.sourceDataPath = nameStub, uniqueName, sourceDataPath

    def __repr__(self):
        return str((self.nameStub, self.uniqueName, self.sourceDataPath))

    def targetFeaturePath(self, targetDataPath):
        """
        Absolute target filename (or prefix) for feature data file (or file prefix).
        @param targetDataPath: basedir to copy to
        """
        return os.path.join(targetDataPath, self.uniqueName, os.path.basename(self.sourceDataPath))

    def copyData(self, targetDataPath, dryRun=False):
        """
        Copy the data files from sourceFeaturePath to targetFeaturePath.
        This is convoluted because:
        * path may be a filename prefix
        * path may be a directory
        In fact, it may be necessary to provide feature function specific rules here...
        @param targetDataPath: basedir to copy to
        """
        targetPath = self.targetFeaturePath(targetDataPath)
        targetBase = os.path.dirname(targetDataPath)
        if not dryRun:
            os.makedirs(targetBase)
        else:
            sys.stderr.write('makedirs(%s)\n' % (targetBase))
        if os.path.isdir(self.sourceDataPath):
            if not dryRun:
                shutil.copytree(self.sourceDataPath, targetPath)
            else:
                sys.stderr.write('copytree(%s, %s)\n' % (self.sourceDataPath, targetPath))
        #elif os.path.isfile():
        #    # BUT: maybe the named one is not the only file... we should still glob.
        else:
            if dryRun:
                sys.stderr.write('copy(%s, %s)\n' % (self.sourceDataPath + '*', targetBase))
            for file in glob.glob(self.sourceDataPath + '*'):
                target = os.path.join(targetBase, os.path.basename(file))
                if not dryRun:
                    shutil.copy(file, target)
                else:
                    sys.stderr.write('  copy(%s, %s)\n' % (file, target))


class MosesIniConverter(MosesIniParser):
    def __init__(self, mosesIni, targetDataPath, logger=None):
        super(MosesIniConverter, self).__init__(mosesIni, logger)
        self.targetDataPath = targetDataPath
        self.convertedIniLines = []

    @overrides(MosesIniParser)
    def handleNonFeatureLine(self, iline, line):
        # replicate other lines we don't care about
        self.convertedIniLines.append(line)

    @overrides(MosesIniParser)
    def handleFeatureLine(self, nameStub, args, iline, line):
        """Replace path if present and append (changed) feature line."""

        # unique name for each feature (e.g. LM0)
        featureName = args['name']

        # the actual core reason why we parsed all the stuff
        if 'path' in args:
            feature = Feature(nameStub, featureName, args['path'])

            # change path to the new targetDataPath-prefixed version
            args['path'] = feature.targetFeaturePath(self.targetDataPath)

            # use new target path in feature line
            line = self.makeFeatureLine(nameStub, args)
            self.pathedFeatures[featureName] = feature

        self.convertedIniLines.append(line)

    def convert(self):
        self.run()
        return '\n'.join(self.convertedIniLines)


args = parseArguments()
args = fixPaths(args)

with open(args.source_moses_ini) as fin:
    converter = MosesIniConverter(fin, args.output_data_path, logger=logging.getLogger())
    result = converter.convert()

with open(args.target_moses_ini, 'w') as fo:
    fo.write(result)

# copy the feature data files for features with a given 'path' attribute
for f in converter.pathedFeatures:
    converter.pathedFeatures[f].copyData(converter.targetDataPath, args.dryRun)
