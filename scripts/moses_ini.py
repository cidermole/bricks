#!/usr/bin/env python
#
# Simple moses.ini parser for feature lines.
#
# Author: David Madl <git@abanbytes.eu>

# ConfigParser is not suitable to parse moses.ini since it contains lines without key-value pairs (without an equals sign.)
# Homebrew moses.ini "parser" FTW.

from collections import Counter
import logging
import glob, os, shutil


def overrides(interface_class):
    def overrider(method):
        assert(method.__name__ in dir(interface_class))
        return method
    return overrider



class Feature:
    """
    Representation of single feature line in moses.ini
    """
    def __init__(self, nameStub, uniqueName, sourceDataPath, logger=None):
        """
        @param nameStub:   PhraseTableMemory
        @param uniqueName: PT0
        @param sourceDataPath: /home/user/models/phrase-table.0-0.1.1.gz
        """
        self.nameStub, self.uniqueName, self.sourceDataPath = nameStub, uniqueName, sourceDataPath
        self.logger = logger

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
            self.logger.info('makedirs(%s)' % (targetBase))
        if os.path.isdir(self.sourceDataPath):
            if not dryRun:
                shutil.copytree(self.sourceDataPath, targetPath)
            else:
                self.logger.info('copytree(%s, %s)' % (self.sourceDataPath, targetPath))
        #elif os.path.isfile():
        #    # BUT: maybe the named one is not the only file... we should still glob.
        else:
            if dryRun:
                self.logger.info('copy(%s, %s)' % (self.sourceDataPath + '*', targetBase))
            for file in glob.glob(self.sourceDataPath + '*'):
                target = os.path.join(targetBase, os.path.basename(file))
                if not dryRun:
                    shutil.copy(file, target)
                else:
                    self.logger.info('  copy(%s, %s)' % (file, target))

    def dataFiles(self):
        # like above (TODO: unify)
        if os.path.isdir(self.sourceDataPath):
            return [self.sourceDataPath]
        else:
            return [file for file in glob.glob(self.sourceDataPath + '*')]


class MosesIniParser(object):
    def __init__(self, mosesIni, logger=None):
        self.logger = logger or logging.getLogger('dummy')
        self.mosesIni = mosesIni
        self.pathedFeatures = {}
        self.description_counts = Counter()  # count unnamed moses features

    def assertOrWarnLine(self, cond, iline, message):
        if not cond:
            self.logger.warning('warning: parsing moses.ini line %d: %s\n' % (iline + 1, message))
        return cond

    def run(self):
        """Parses moses.ini and executes parseFeatureLine() for each feature line."""
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

            if not parseLine:
                self.handleNonFeatureLine(iline, line)
            else:
                self.parseFeatureLine(iline, line)

    def parseFeatureLine(self, iline, line):
        """Parse a feature line and handle it."""
        parts = line.split(' ')
        nameStub = parts[0]
        assert(len(nameStub) > 0)  # skipping empty lines guarantees this

        try:
            # len(t) > 0 filters out duplicate spaces
            args = dict([tuple(t.split('=')) for t in parts[1:] if len(t) > 0])
        except ValueError:
            self.assertOrWarnLine(False, iline, 'failed to parse feature line key-value pairs')
            raise

        # automatic naming for features without a name=, just like in moses
        if not 'name' in args:
            c = self.description_counts[nameStub]
            self.description_counts[nameStub] += 1
            args['name'] = nameStub + str(c)

        self.handleFeatureLine(nameStub, args, iline, line)

    def handleNonFeatureLine(self, iline, line):
        """Parse a moses.ini line that is not a feature definition."""
        pass

    def handleFeatureLine(self, nameStub, args, iline, line):
        """
        Called for each feature line in moses.ini.
        @param nameStub: PhraseTableMemory
        @param args:     dict of string key-value pairs in feature config line
        @param iline:    0-based file line
        @param line:     original feature line
        """
        pass

    def makeFeatureLine(self, nameStub, args):
        return '%s %s' % (nameStub, ' '.join(['='.join(t) for t in args.items()]))
