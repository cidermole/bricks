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


# Self-converting on copyData()
class ProbingPTFeature(Feature):
    def __init__(self, _, uniqueName, sourceDataPath, logger=None):
        super(ProbingPTFeature, self).__init__('ProbingPT', uniqueName, sourceDataPath, logger)

    @overrides(Feature)
    def targetFeaturePath(self, targetDataPath, _=None):
        # change path to the new targetDataPath-prefix (points to directory for ProbingPT, but dirname is taken of this)
        return Feature.targetFeaturePath(self, targetDataPath, targetBaseName='nonexist')

    @overrides(Feature)
    def copyData(self, targetDataPath, noOverwrite=False, dryRun=False):
        fs = FancyCopy(noOverwrite, dryRun)
        targetPath = self.targetFeaturePath(targetDataPath)
        targetBase = os.path.dirname(targetPath)

        fs.makedirs(targetBase)

        if not dryRun:
            num_scores = 4
            subprocess.check_call(['CreateProbingPT', self.sourceDataPath, targetBase, str(num_scores)])
        else:
            self.logger.info('convert(%s, %s)' % (self.sourceDataPath, targetBase))


class MosesIniPhraseTableConverter(MosesIniConverter):
    @overrides(MosesIniConverter)
    def featureClass(self, nameStub):
        # change from PhraseDictionaryMemory to ProbingPT
        if nameStub == 'PhraseDictionaryMemory':
            return ProbingPTFeature
        else:
            return MosesIniConverter.featureClass(self, nameStub)


if __name__ == '__main__':
    moses_ini_copy_setup.main(MosesIniPhraseTableConverter)
