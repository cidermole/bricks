#!/usr/bin/env python2
#
# bricks.py prepares an SMT experiment from shell script templates and
# a configuration file.
#
# File Paths
# ----------
# * Including config files
#   * relative path: key: @"include.cfg"
#       (FIXME) currently refers to the working directory. Should be relative from the config file location.
#   * absolute path: key: @<Bricks.cfg>
#       searched for in bricks/ and can be used from anywhere.
#
# * Jinja template files
#     Jinja2 has its own search path implementation. We add bricks/
#     to its search path.
#
# * Input and output files in Bricks
#     Brick inputs and outputs are symlinked relative to the Brick
#     working directory, e.g. input/src input/trg output/alignment
#
#     Use absolute paths for Experiment input files residing somewhere
#     outside the experiment.
#       note: relative paths to input files are not resolved yet.
#       They currently are relative to the Brick working directory.
#
# Brick script execution
# ----------------------
# Happens via 'redo', each script is run in its Brick working directory.
# 'bricks.py' sets up a hierarchy of working directories for Bricks,
# with symlinks of inputs (and outputs for Bricks containing parts.)
#
# number of run (always 0 currently, incremental experiments not implemented)
# |
# v   name of Brick (outermost Brick is always called Experiment)
# 0/  v
#     Experiment/
#         input/rawCorpusSource -> /data/raw.corpus.en
#         input/rawCorpusTarget -> /data/raw.corpus.it
#         output/alignment -> WordAligner0/output/alignment
#
#         PrepSrc/
#             input/raw -> ../../input/rawCorpusSource
#             output/truecased            < not actually created by bricks.py
#             <...>
#
#         PrepTrg/
#             input/raw -> ../../input/rawCorpusTarget
#             output/truecased            < not actually created by bricks.py
#             <...>
#
#         WordAligner0/
#             # links dangle (target doesn't exist) until actual run of Prep*
#             input/src -> ../../PrepSrc/output/truecased
#             input/trg -> ../../PrepTrg/output/truecased
#
#             Giza12/
#                 input/crp1 -> ../../input/src
#                 <...>
#
# Templates
# ---------
# The idea of the shell script wrappers around programs, specified in Bricks
# either directly as a Jinja template string using 'template:' or as a Jinja
# template file name 'templateFile:', is to
#
# 1) specify both overridable and default configuration values to helpers,
#
# 2) coerce helper programs to take their input and produce their output
#    exactly in this filesystem structure. (Temporary files are often also
#    created, but should never be referred to by other Bricks).
#
#
# incremental experiments
# -----------------------
# The idea for incremental experiments will be to check via 'redo' if targets
# need to be run, and if they don't, we can symlink their input back to the
# previous run.
#

from __future__ import print_function

import re
import config
import os
import sys
import jinja2


class Brick(config.Mapping):
    """
    Wrapper around config.Mapping with various utility functions for Bricks.
    """
    def __init__(self, mapping):
        config.Container.__init__(self, mapping.parent)
        object.__setattr__(self, 'path', mapping.path)
        object.__setattr__(self, 'data', mapping.data)
        object.__setattr__(self, 'order', mapping.order)
        object.__setattr__(self, 'comments', mapping.comments)

        # rudimentarily assert that this config level is indeed a Brick
        assert('input' in self.data and 'output' in self.data)

    def filesystemPath(self, configPath=None):
        """
        Map the config path to a relative filesystem path of the experiment
        directory which will contain this Brick's data for the runner system.
        """
        # replace .parts: shortens "Experiment.parts.WordAligner0.parts.Giza12"
        # into "Experiment.WordAligner0.Giza12"
        configPath = self.path if configPath is None else configPath
        configPath = filter(None, re.split(r"[%s]+" % re.escape(".[]"), configPath))
        path = ['0']
        path += [part for part in configPath if part != "parts"]
        return os.path.join(*path)

    def findConfig(self, container):
        # clone from config.Reference
        while (container is not None) and not isinstance(container, config.Config):
            container = object.__getattribute__(container, 'parent')
        return container

    def magicInputBrick(self, inputRef):
        assert(type(inputRef) is config.Reference)
        #print(inputRef.path)
        #return "<input magic>"
        # brick.input.reorderingTables.data[0].relativePath(brick)[:-2]

        # relative path to referenced Brick
        refBrickPathOrig = inputRef.relativePath(self)[:-2]
        refBrickPath = list(refBrickPathOrig)

        # absolute path of us
        ourPath = self.path.split('.')

        # resolve relative _ walking upwards
        # (poor man's implementation)
        resPoint = self
        while refBrickPath[0] == '_':
            refBrickPath = refBrickPath[1:]
            ourPath = ourPath[:-1]
            resPoint = resPoint.parent

        completePath = ourPath + refBrickPath

        #sys.stderr.write('resolved: %s\n' % '.'.join(completePath))

        # getting stuff from the original Config, we do not have the inheritance resolved :(
        #inputBrick = self.findConfig(self).getByPath('.'.join(completePath))

        # new walking resolution method
        inputBrick = resPoint.getByPath('.'.join(refBrickPath))
        #inputBrick = self.parent.getByPath('.'.join(refBrickPath))

        #inputBrick = '.'.join(refBrickPathOrig)
        #inputBrick = self.parent.LexReord0

        #sys.stderr.write('%s\n' % str(inputBrick))

        return inputBrick


    def pwd(self):
        """
        Absolute path to this Brick's working directory. Used from Jinja.
        """
        return os.path.abspath(self.filesystemPath())

    def referenceDependencyPath(self, relativePath, brickOnly=True):
        """
        Turns a config path referencing another Brick into a filesystem path.
        Used for adding dependencies to the runner system.
        @param relativePath list of node names along config path
        @param brickOnly    only reference the brick itself, not the actual input/output file
        """
        #print(brickOnly, relativePath)

        # currently we only support dependencies of the form ...:

        # ['_', '_', 'Giza12', 'output', 'alignment']
        # used for input dependencies
        if len(relativePath) == 5 and relativePath[0:2] == ['_', '_'] \
                and relativePath[3] != '_' and relativePath[3] == 'output':
            if brickOnly:
                return os.path.join('..', relativePath[2], 'brick')
            else:
                return os.path.join(*(['..'] + relativePath[2:5]))

        # ['_', '_', '_', 'input', 'src']
        # ['_', '_', '_', 'input', 'corpora', '0'] - for referencing input lists
        # used in referencing the Brick's input in parts
        if len(relativePath) in [5, 6] and relativePath[0:3] == ['_', '_', '_'] \
                and relativePath[3] in ['output', 'input']:
            if brickOnly:
                return None
            else:
                return os.path.join(*(['..'] + relativePath[3:]))

        # ['_', 'parts', 'WordAligner0', 'output', 'alignment']
        # used for output dependencies
        if len(relativePath) == 5 and relativePath[0:2] == ['_', 'parts'] \
                and relativePath[3] == 'output':
            if brickOnly:
                return os.path.join(relativePath[2], 'brick')
            else:
                return os.path.join(*relativePath[2:5])

        return None

    def dependencies(self):
        """
        Get all Bricks which we depend on, as a list of relative
        file paths for the runner system 'redo'.
        Either 'input' dependencies, or 'output' dependencies
        (the latter for Bricks with parts).
        Used from 'brick.do.jinja' to obtain dependencies for 'redo'.
        """
        dependencies = set()

        for inout in ['input', 'output']:
            mapping = self[inout]

            # walk this Brick's anyputs without resolving config keys
            for (key, anyput) in mapping.data.iteritems():
                if type(anyput) is config.Reference:
                    # we may be referencing another Brick, which we then
                    # need to add as a dependency.
                    relPath = anyput.relativePath(mapping)
                    path = self.referenceDependencyPath(relPath)
                    if path is not None:
                        dependencies.add(path)

        # TODO input Sequences

        return dependencies

    def linkPaths(self, inout, apParent, anyput, key, linkSourcePref, linkTarget):
        """
        Recursively walk inputs/outputs and link a list of path tuples.
        """
        inoutMapping = {'input': self.input, 'output': self.output}[inout]
        linkSource = None

        if type(anyput) is config.Mapping:
            # walk this Brick's *puts without resolving config keys
            for (k, aput) in anyput.data.iteritems():
                self.linkPaths(inout, anyput, aput, k, os.path.join(linkSourcePref, '..'), os.path.join(linkTarget, k))
        elif type(anyput) is config.Sequence:
            for (i, aput) in enumerate(anyput.data):
                # anyput??
                self.linkPaths(inout, anyput, aput, i, os.path.join(linkSourcePref, '..'), os.path.join(linkTarget, str(i)))
        elif type(anyput) is config.Reference:
            # referencing another Brick
            relPath = anyput.relativePath(inoutMapping)
            linkSource = self.referenceDependencyPath(relPath, brickOnly=False)
        elif type(anyput) is bool:
            # no specification at all, e.g. output: { trg }
            # here, config parser falls back to defining a bool trg=True
            # (not an output dependency)
            if inout == 'input':
                raise ValueError("input %s of Brick %s is neither connected nor defined as a file." % (key, self.path))
        else:
            # str, or config.Expression: a direct filename specification.
            #sys.stderr.write("STR %s\n" % inp)

            # potentially resolves config.Expression here
            # why pass apParent? because config.Expression doesn't have .parent
            linkSource = apParent[key]

            # for input, check if file exists in FS
            if inout == 'input' and not os.path.exists(linkSource):
                raise ValueError("input %s of Brick %s = %s does not exist in file system." % (key, self.path, anyput))

        if linkSource is not None:
            linkSource = os.path.join(linkSourcePref, linkSource)
            #sys.stderr.write("%s -> %s\n" % (linkSource, linkTarget))

            # mkdir -p $(dirname linkTarget)
            if not os.path.exists(os.path.dirname(linkTarget)):
                os.makedirs(os.path.dirname(linkTarget))
            # ln -sf linkSource linkTarget
            if os.path.islink(linkTarget):
                os.unlink(linkTarget)
            os.symlink(linkSource, linkTarget)

    def createSymlinks(self, inout):
        """
        Create symlinks for all inputs/outputs.
        @param inout either 'input' or 'output'
        """
        inoutMapping = {'input': self.input, 'output': self.output}[inout]

        fsPath = self.filesystemPath()

        # ensure each Brick has an input/output directory
        if not os.path.exists(os.path.join(fsPath, inout)):
            os.makedirs(os.path.join(fsPath, inout))

        self.linkPaths(inout, self, inoutMapping, inout, '', os.path.join(fsPath, inout))


# can we create this while copying the config tree for inheritance?
class InputWrap(object):
    """
    Wraps a Brick input config for easy access from Jinja templates.
    """
    def __init__(self, brick, reference, fileStr):
        """
        @param reference: config.Reference pointing to output, or str otherwise?
        """
        self.brick = brick
        self.refOrStr = reference
        self.fileStr = fileStr
        self.mib = self.brick.magicInputBrick(self.refOrStr)

    def __str__(self):
        """
        @return: input file path for our Brick, relative to Brick working directory.
        """
        # TODO: this could be absolute path, if config files usually need that (I think so)
        return self.fileStr

    def __repr__(self):
        return self.__str__()

    def __getattr__(self, item):
        """
        Allow simplified access (easy syntax) to input Brick's config in
        Jinja templates. Syntax example: {{ brick.input.phraseTable.reorderingConfigSpec }}
        """
        if item in self.mib:
            return self.mib[item]
        else:
            return object.__getattribute__(self, item)


class TemplateBrick(Brick):
    """
    Wrapper around Brick to replace input and output with nice wrappers
    for access from templates.
    """
    def __init__(self, brick):
        Brick.__init__(self, brick)

    def __getattribute__(self, item):
        if item != 'input':
            # resort to our parent with all other attributes
            return Brick.__getattribute__(self, item)

        # override the attributes input, output
        anyputMap = {}
        #anyputs = Brick.__getattribute__(self, item)
        anyputs = self.data[item]
        for anyput in anyputs.keys():
            val = anyputs.data[anyput]
            if type(val) is config.Reference:
                # TODO: fsPath() on Reference
                anyputMap[anyput] = InputWrap(self, val, os.path.join(item, anyput))
            elif type(val) is config.Sequence:
                l = []
                #for i, v in enumerate(val):
                #    l.append(InputWrap(self, v, os.path.join(item, anyput, str(i))))
                for i in range(len(val)):
                    if type(val.data[i]) is config.Reference:
                        # avoid resolving key in Sequence
                        l.append(InputWrap(self, val.data[i], os.path.join(item, anyput, str(i))))
                    else:
                        # potentially resolve key
                        l.append(val[i])
                anyputMap[anyput] = l
            else:
                # potentially resolve key
                anyputMap[anyput] = anyputs[anyput]
            # bla, bla. the usual input processing. why do I keep repeating it?
            # need recursion for resolving References in a Sequence

            # TODO: maybe a processing helper with a callback?
            # either callback, or map()-like interface (like here), ...
        return anyputMap


class ConfigGenerator(object):
    def __init__(self, cfgFileName, searchPath):
        configSearchPath = config.ConfigSearchPath([searchPath])
        cfg = config.Config(file(cfgFileName), searchPath=configSearchPath).instantiate()
        self.experiment = cfg.Experiment
        self.searchPath = searchPath
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=searchPath))

    def replaceFileContents(self, fileName, newContents):
        """
        Only replace fileName with newContents if the contents differ
        from what the file currently contains.
        This avoids changing mtime of the file and thus avoids the
        runner system re-running bricks which haven't changed.
        """
        if os.path.exists(fileName):
            with open(fileName) as fi:
                oldContents = fi.read()
            if oldContents == newContents:
                # no need to update the file
                return

        # create directory if necessary
        if not os.path.exists(os.path.dirname(fileName)):
            os.makedirs(os.path.dirname(fileName))

        with open(fileName, 'w') as fo:
            fo.write(newContents)

    def generateRedoFile(self, brick):
        """
        Generate a redo file from template for this Brick.
        """
        if 'template' in brick:
            # short specification of Jinja template for {% block Work %}
            with open(os.path.join(self.searchPath, 'template.do.jinja')) as fi:
                # 1) Python string interpolation in %%s (from 'template:')
                # 2) Jinja template expansion
                template = self.env.from_string(fi.read() % brick.template)
        elif 'templateFile' in brick:
            # load specified Jinja template file
            template = self.env.get_template(brick.templateFile)
        else:
            # default fallback - nothing to do (but still checks dependencies)
            template = self.env.get_template('brick.do.jinja')

        # Render the Jinja template
        brickDo = template.render({'brick': TemplateBrick(brick)})

        # create/replace redo file, if necessary
        targetFile = os.path.join(brick.filesystemPath(), 'brick.do')
        self.replaceFileContents(targetFile, brickDo)

    def generateBricks(self, cfgBrick):
        """
        Recursively generate a config for this Brick and all
        its parts.
        @param cfgBrick config.Mapping entry for this Brick.
        """
        # we know / assume that this config.Mapping is a Brick.
        brick = Brick(cfgBrick)

        # nice debug prints
        #sys.stderr.write('%s\n' % cfgBrick.path)
        #if len(brick.inputDependencies()) > 0:
        #    sys.stderr.write('  input %s\n' % str(brick.inputDependencies()))
        #if len(brick.outputDependencies()) > 0:
        #    sys.stderr.write('  output %s\n' % str(brick.outputDependencies()))

        brick.createSymlinks('input')
        brick.createSymlinks('output')
        self.generateRedoFile(brick)

        if 'parts' in brick:
            for part in brick.parts.keys():
                self.generateBricks(brick.parts[part])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write('usage: %s <example.cfg>\n' % sys.argv[0])
        sys.stderr.write('generates the experiment in current working directory.\n')
        sys.exit(1)

    # search path for both global config includes @<Bricks.cfg>
    # and Jinja templates.
    appDir = os.path.dirname(os.path.realpath(__file__))
    searchPath = os.path.join(appDir, 'bricks')

    gen = ConfigGenerator(sys.argv[1], searchPath)
    gen.generateBricks(gen.experiment)

    # ~/mmt/redo/redo == redo
    sys.stderr.write('Now run the experiment using $ ~/mmt/redo/redo 0/Experiment/brick\n')
