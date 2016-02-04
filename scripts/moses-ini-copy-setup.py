#!/usr/bin/env python
#
# Copies moses.ini and model files referenced within to a new location,
# producing a modified moses.ini pointing to the files in the new location.
#
# Author: David Madl <git@abanbytes.eu>

import sys
import os
import glob
import shutil
import argparse
import logging
from moses_ini import MosesIniParser, Feature, overrides


def parseArguments():
    parser = argparse.ArgumentParser(description='Copies a moses.ini file to a new location while ' +
                                                 'also copying the referenced data files.')
    parser.add_argument('-f', '--input', dest='source_moses_ini', help='moses.ini in its original environment', nargs='?', default='/dev/stdin')
    parser.add_argument('-o', '--output', dest='target_moses_ini', help='target path to moses.ini or directory to store moses.ini', nargs='?', default='/dev/stdout')
    parser.add_argument('output_data_path', help='target path to a directory to store data files')
    parser.add_argument('-n', '--no-overwrite-data', dest='noOverwrite', help='do not overwrite data files if they already exist', action='store_true')
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
            #featureClass = Feature
            featureClass = self.featureClass(nameStub)
            feature = featureClass(nameStub, featureName, sourceDataPath=args['path'], logger=self.logger)

            # change path to the new targetDataPath-prefixed version
            args['path'] = feature.targetFeaturePath(self.targetDataPath)

            # use new target path in feature line
            line = self.makeFeatureLine(nameStub, args)
            self.pathedFeatures[featureName] = feature

        self.convertedIniLines.append(line)

    def featureClass(self, nameStub):
        return Feature

    def convert(self):
        self.run()
        return '\n'.join(self.convertedIniLines)


def main(mosesIniConverterClass):
    args = parseArguments()
    args = fixPaths(args)

    logging.basicConfig(level=logging.INFO)

    with open(args.source_moses_ini) as fin:
        converter = mosesIniConverterClass(fin, args.output_data_path, logger=logging.getLogger())
        result = converter.convert()

    with open(args.target_moses_ini, 'w') as fo:
        fo.write(result)

    # copy the feature data files for features with a given 'path' attribute
    for f in converter.pathedFeatures:
        converter.pathedFeatures[f].copyData(converter.targetDataPath, args.noOverwrite, args.dryRun)


if __name__ == '__main__':
    main(MosesIniConverter)
