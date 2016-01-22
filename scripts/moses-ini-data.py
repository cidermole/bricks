#!/usr/bin/env python
#
# Dumps feature model files from moses.ini (includes the resolution of prefixes), one per line.
#
# Author: David Madl <git@abanbytes.eu>

import argparse
import logging
from moses_ini import MosesIniParser, Feature, overrides


def parseArguments():
    parser = argparse.ArgumentParser(description='Dumps feature model files from moses.ini (includes the resolution ' +
                                                 'of prefixes), one per line.')
    parser.add_argument('-f', '--input', dest='source_moses_ini', help='moses.ini', nargs='?', default='/dev/stdin')

    args = parser.parse_args()

    return args


class MosesIniDataFiles(MosesIniParser):
    def __init__(self, mosesIni, logger=None):
        super(MosesIniDataFiles, self).__init__(mosesIni, logger)
        self.dataFileSet = set()

    @overrides(MosesIniParser)
    def handleFeatureLine(self, nameStub, args, iline, line):
        if 'path' in args:
            feature = Feature(nameStub, args['name'], args['path'], logger=self.logger)
            self.dataFileSet.update(feature.dataFiles())

    def dataFiles(self):
        self.run()
        return self.dataFileSet


args = parseArguments()

with open(args.source_moses_ini) as fin:
    df = MosesIniDataFiles(fin, logger=logging.getLogger())
    result = df.dataFiles()
    for f in result:
        print(f)
