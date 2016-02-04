#!/usr/bin/env python
#
# Change the phrase table in moses.ini, with potential model conversion.
#
# Needs CreateProbingPT on the PATH.
#
# Author: David Madl <git@abanbytes.eu>

import argparse
import logging
import os
import subprocess
from moses_ini import MosesIniParser, Feature, FancyCopy, overrides
# TODO: change filename
moses_ini_copy_setup = __import__("moses-ini-copy-setup")
MosesIniConverter = moses_ini_copy_setup.MosesIniConverter


def argumentParser():
    parser = argparse.ArgumentParser(description='Copies a moses.ini file to a new location while ' +
                                                 'also copying the referenced data files.')
    moses_ini_copy_setup.addArguments(parser)
    parser.add_argument('-t', '--phrase-table', dest='phraseTable', help='Phrase table to use.')
    parser.add_argument('-l', '--compact-lexicalized-reordering', dest='compactLexicalizedReordering', help='use compact LR table.', action='store_true')
    return parser


# Self-converting on copyData()
class ConvertingFeature(Feature):
    def __init__(self, nameStub, uniqueName, sourceDataPath, logger=None):
        super(ConvertingFeature, self).__init__(nameStub, uniqueName, sourceDataPath, logger)
        self.targetBaseName = ''

    @overrides(Feature)
    def targetFeaturePath(self, targetDataPath, _=None):
        # change path to the new targetDataPath-prefix (points to directory for ProbingPT)
        return Feature.targetFeaturePath(self, targetDataPath, targetBaseName=self.targetBaseName)

    @overrides(Feature)
    def copyData(self, targetDataPath, noOverwrite=False, dryRun=False):
        fs = FancyCopy(noOverwrite, dryRun)
        targetPath = self.targetFeaturePath(targetDataPath)
        targetBase = os.path.dirname(targetPath)

        fs.makedirs(targetBase)

        if not dryRun:
            self.copyStub(targetPath)
        else:
            self.logger.info('convert(%s, %s)' % (self.sourceDataPath, targetPath))

    def copyStub(self, targetBase):
        pass


class ProbingPTFeature(ConvertingFeature):
    def __init__(self, _, uniqueName, sourceDataPath, logger=None):
        # use output name here
        super(ProbingPTFeature, self).__init__('ProbingPT', uniqueName, sourceDataPath, logger)
        self.targetBaseName = ''

    @overrides(ConvertingFeature)
    def copyStub(self, targetPath):
        num_scores = 4
        os.makedirs(targetPath)
        subprocess.check_call(['CreateProbingPT', self.sourceDataPath, targetPath, str(num_scores)])

class CompactPTFeature(ConvertingFeature):
    def __init__(self, _, uniqueName, sourceDataPath, logger=None):
        # use output name here
        super(CompactPTFeature, self).__init__('PhraseDictionaryCompact', uniqueName, sourceDataPath, logger)
        self.targetBaseName = 'phrase-table'

    @overrides(ConvertingFeature)
    def copyStub(self, targetPath):
        subprocess.check_call(['processPhraseTableMin', '-in', self.sourceDataPath, '-out', targetPath])

class CompactLRFeature(ConvertingFeature):
    def __init__(self, _, uniqueName, sourceDataPath, logger=None):
        # use output name here
        super(CompactLRFeature, self).__init__('LexicalReordering', uniqueName, sourceDataPath, logger)
        self.targetBaseName = 'reordering-table'

    @overrides(ConvertingFeature)
    def copyStub(self, targetPath):
        subprocess.check_call(['processLexicalTableMin', '-in', self.sourceDataPath, '-out', targetPath])



class MosesIniPhraseTableConverter(MosesIniConverter):
    def __init__(self, mosesIni, args, logger=None):
        super(MosesIniPhraseTableConverter, self).__init__(mosesIni, args, logger)
        ptFeatures = {
            'ProbingPT': ProbingPTFeature,
            'PhraseDictionaryCompact': CompactPTFeature
        }
        # convert from: to
        self.convFeatures = {
            'PhraseDictionaryMemory': ptFeatures[args.phraseTable]
        }
        if args.compactLexicalizedReordering:
            self.convFeatures.update({ 'LexicalReordering': CompactLRFeature })

    @overrides(MosesIniConverter)
    def featureClass(self, nameStub):
        if nameStub in self.convFeatures:
            return self.convFeatures[nameStub]
        else:
            return MosesIniConverter.featureClass(self, nameStub)


if __name__ == '__main__':
    moses_ini_copy_setup.main(MosesIniConverter, argumentParser())
