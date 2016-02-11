#!/usr/bin/env python2
#
# bricks.py prepares an SMT experiment from shell script templates and
# a configuration file.
#
# File Paths
# ----------
# * Including config files
#   * relative path: key: @"include.cfg"
#       relative to the respective config file, or the working
#       directory if not itself included.
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

from brick_config import config
import logging
import os
import shutil
import sys
import jinja2
import argparse


class Brick(config.Mapping):
    """
    Wrapper around config.Mapping with various utility functions for Bricks.
    """
    def __init__(self, mapping):
        assert(isinstance(mapping, config.Mapping))
        config.Container.__init__(self, mapping.parent)
        object.__setattr__(self, 'path', mapping.path)
        object.__setattr__(self, 'data', mapping.data)
        object.__setattr__(self, 'order', mapping.order)
        object.__setattr__(self, 'comments', mapping.comments)
        object.__setattr__(self, 'resolving', set())

        # rudimentarily assert that this config level is indeed a Brick
        if not ('input' in self.data and 'output' in self.data):
            raise ValueError("Brick %s is missing an input: or output: block" % self.path)

    def filesystemPath(self, configPath=None):
        """
        Map the config path to a relative filesystem path of the experiment
        directory which will contain this Brick's data for the runner system.
        """
        # replace .parts: shortens "Experiment.parts.WordAligner0.parts.Giza12"
        # into "Experiment/WordAligner0/Giza12"
        configPath = self.pathParts()
        path = ['0']
        path += [part for part in configPath if part != "parts"]
        return os.path.join(*path)

    def magicInputBrick(self, inputRef):
        """
        For a given Brick input Reference, return the Brick which provides this input.
        @param inputRef: Reference from the input mapping of a Brick, referring to another Brick's output
        """
        assert(type(inputRef) is config.Reference)

        # relative path to referenced Brick
        refBrickPathOrig = inputRef.relativePath(self)[:-2]
        refBrickPath = list(refBrickPathOrig)

        # absolute path of us
        ourPath = self.path.split('.')

        # TODO: see below comment with this wording: "magicInputBrick() should have gone this route."
        # TODO: but need to remember parent in resolve2() since this may be a Reference itself, which
        # TODO: doesn't have a parent.

        # resolve relative _ walking upwards
        # (poor man's implementation)
        resPoint = self
        while len(refBrickPath) > 0 and refBrickPath[0] == '_':
            refBrickPath = refBrickPath[1:]
            ourPath = ourPath[:-1]
            resPoint = resPoint.parent

        #sys.stderr.write('resolved: %s\n' % '.'.join(ourPath + refBrickPath))

        inputBrick = resPoint.getByPath('.'.join(refBrickPath))  if len(refBrickPath) > 0 else resPoint
        #sys.stderr.write('%s\n' % str(inputBrick))

        return inputBrick

    def pwd(self):
        """
        Absolute path to this Brick's working directory. Used from Jinja.
        """
        return os.path.abspath(self.filesystemPath())

    def referenceDependencyPath(self, anyput, container, brickOnly=True, depth=0):
        """
        Turns a config path referencing another Brick into a filesystem path.
        Used for adding dependencies to the runner system.
        @param relativePath list of node names along config path
        @param brickOnly    only reference the brick itself, not the actual input/output file
        """
        #print(brickOnly, relativePath)

        relativePath = anyput.relativePath(container)[depth:]

        # This should really, really be integrated in a recursive function which walks
        # the config tree. However, this is how it has grown. Feel free to replace this.

        # currently we only support dependencies of the form ...:

        # ['_', '_', 'Giza12', 'output', 'alignment']
        # used for input dependencies (of siblings)
        if len(relativePath) in [5, 6] and relativePath[0:2] == ['_', '_'] \
                and relativePath[2] != '_' and relativePath[3] == 'output':
            if brickOnly:
                return os.path.join('..', relativePath[2], 'brick')
            else:
                return os.path.join(*(['..'] + relativePath[2:]))

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
        # ['_', 'parts', 'Split0', 'output', 'texts', '0']
        # used for output dependencies
        if len(relativePath) in [5, 6] and relativePath[0:2] == ['_', 'parts'] \
                and relativePath[3] == 'output':
            if brickOnly:
                return os.path.join(relativePath[2], 'brick')
            else:
                return os.path.join(*relativePath[2:])

        return None

    def dependencies(self, depType=None):
        """
        Get all Bricks which we depend on, as a list of relative
        file paths for the runner system 'redo'.
        Either 'input' dependencies, or 'output' dependencies
        (the latter for Bricks with parts).
        Used from 'brick.do.jinja' to obtain dependencies for 'redo'.
        """
        allDependencies = list()

        types = ['input', 'output'] if depType is None else [depType]

        # add input dependencies first:
        # >> Inputs need to be run before the outputs. <<
        #
        # To run parallelized, all inputs may be run in parallel, but must be
        # finished before the "outputs" (brick parts) are run.

        for inout in types:
            dependencies = set()
            mapping = self[inout]

            # walk this Brick's anyputs without resolving config keys
            for (key, anyput) in mapping.data.iteritems():
                if type(anyput) is config.Reference:
                    # we may be referencing another Brick, which we then
                    # need to add as a dependency.
                    path = self.referenceDependencyPath(anyput, mapping)
                    if path is not None:
                        dependencies.add(path)
                elif isinstance(anyput, config.Sequence):
                    # get dependencies from input Sequences
                    for val in anyput.data:
                        if type(val) is config.Reference:
                            path = self.referenceDependencyPath(val, anyput, depth=1)
                            if path is not None:
                                dependencies.add(path)

            allDependencies += sorted(list(dependencies))

        return allDependencies

    def linkPaths(self, inout, apParent, anyput, key, linkSourcePref, linkTarget):
        """
        Recursively walk inputs/outputs and create symlinks in the filesystem.
        """
        inoutMapping = {'input': self.input, 'output': self.output}[inout]
        resultList = []
        linkSource = None

        if type(anyput) is config.Mapping:
            # walk this Brick's *puts without resolving config keys
            for (k, aput) in anyput.data.iteritems():
                resultList += self.linkPaths(inout, anyput, aput, k, os.path.join(linkSourcePref, '..'), os.path.join(linkTarget, k))
        elif isinstance(anyput, config.Sequence):
            for (i, aput) in enumerate(anyput.data):
                # anyput??
                resultList += self.linkPaths(inout, anyput, aput, i, os.path.join(linkSourcePref, '..'), os.path.join(linkTarget, str(i)))
        elif type(anyput) is config.Reference:
            # referencing another Brick
            linkSource = self.referenceDependencyPath(anyput, inoutMapping, brickOnly=False)
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

            resultList.append((linkSource, linkTarget))

        return resultList

    def fsCreateSymlinks(self, links):
        for linkSource, linkTarget in links:
            # mkdir -p $(dirname linkTarget)
            if not os.path.exists(os.path.dirname(linkTarget)):
                os.makedirs(os.path.dirname(linkTarget))
            # ln -sf linkSource linkTarget
            if os.path.islink(linkTarget) or os.path.isfile(linkTarget):
                os.unlink(linkTarget)
            os.symlink(linkSource, linkTarget)

    def inoutSymlinks(self, inout):
        """
        Create symlinks for all inputs/outputs.
        @param inout either 'input' or 'output'
        """
        inoutMapping = {'input': self.input, 'output': self.output}[inout]

        fsPath = self.filesystemPath()

        # TODO: old stuff, remove.
        # ensure each Brick has an input/output directory
        if not os.path.exists(os.path.join(fsPath, inout)):
            os.makedirs(os.path.join(fsPath, inout))

        return self.linkPaths(inout, self, inoutMapping, inout, '', os.path.join(fsPath, inout))

    def symlinks(self):
        sym = []
        sym += self.inoutSymlinks('input')
        sym += self.inoutSymlinks('output')
        return sym


# can we create this while copying the config tree for inheritance?
class InputWrap(object):
    """
    Wraps a Brick input config for easy access from Jinja templates.
    """
    def __init__(self, brick, magicInputBrick, fileStr):
        """
        @param reference: config.Reference pointing to output, or str otherwise?
        """
        self.brick = brick
        self.fileStr = fileStr
        self.mib = magicInputBrick

    def __str__(self):
        """
        To easily obtain brick input filenames from Jinja, for example as {{ brick.input.corpus }}
        This could be written "input/corpus", but becomes more useful in loops over input lists.
        @return: absolute input file path for our Brick.
        """
        return os.path.join(self.brick.pwd(), self.fileStr)

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

        # override the attribute input: make Jinja see a dict of InputWrap instances,
        # or lists of InputWraps for input lists.
        anyputMap = {}
        anyputs = self.data[item]
        for anyput in anyputs.keys():
            val = anyputs.data[anyput]
            resolved = anyputs[anyput]
            if isinstance(resolved, config.Sequence):
                # are we referencing something that is eventually a Sequence?
                # In this case, our input brick must be the same for all Sequence entries.
                if type(val) is config.Reference:
                    magicInput = self.magicInputBrick(val)
                else:
                    magicInput = None

                # wrap input list mapping
                l = []
                for i in range(len(resolved)):
                    if type(resolved.data[i]) is config.Reference:
                        # avoid resolving key in Sequence
                        mib = magicInput if magicInput is not None else self.magicInputBrick(val.data[i])
                        l.append(InputWrap(self, mib, os.path.join(item, anyput, str(i))))
                    else:
                        # potentially resolve key
                        l.append(resolved[i])
                anyputMap[anyput] = l
            elif type(val) is config.Reference:
                # wrap plain input mapping
                # rather, put an fsPath() implementation on Reference?
                anyputMap[anyput] = InputWrap(self, self.magicInputBrick(val), os.path.join(item, anyput))
                # TODO: config.Reference does not necessarily mean this is a mapping to an output. It could be referring to a hardcoded filename.
            else:
                # resolve other keys if necessary (e.g. hardcoded filenames, pieced together)
                #anyputMap[anyput] = anyputs[anyput]
                anyputMap[anyput] = resolved
            # bla, bla. the usual input processing. why do I keep repeating it?
            # need recursion for resolving References in a Sequence

            # TODO: maybe a processing helper with a callback?
            # either callback, or map()-like interface (like here), ...
        return anyputMap


class ConfigGenerator(object):
    def __init__(self, cfgFileName, setupFileName=None, logLevel=logging.ERROR):
        # Logging
        ch = logging.StreamHandler()
        config.logger.addHandler(ch)
        config.logger.setLevel(logLevel)

        # Paths

        # search path for both global config includes @<Bricks.cfg>
        # and Jinja templates.
        try:
            appDir = os.path.dirname(os.path.realpath(__file__))
        except NameError:
            # for interactive Python use
            sys.stderr.write('warning: cannot resolve appDir, interactive mode in %s\n' % os.getcwd())
            appDir = os.getcwd()
        self.appDir = appDir
        searchPath = os.path.join(appDir, 'bricks')

        self.searchPath = searchPath
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=searchPath))
        configSearchPath = config.ConfigSearchPath([searchPath])

        if setupFileName is None:
            setupFileName = 'Setups/%s.cfg' % os.uname()[1].capitalize()
        # resolve relative path in bricks program root
        setupFileName = configSearchPath.searchGlobalFile(setupFileName)

        # Create basic Config (not instantiated, i.e. no inheritance or loops)
        self.cfg = config.Config(file(cfgFileName), searchPath=configSearchPath)
        setup = config.Config(setupFileName, parent=self.cfg, searchPath=configSearchPath)
        # implicit str $BRICKS: path to bricks program root directory
        if not 'BRICKS' in setup:
            setup.BRICKS = appDir

        # implicit Mapping $Setup: Experiment can inherit $Setup for machine-specific config keys
        self.cfg.Setup = setup

    def instantiate(self):
        # resolve inheritance
        self.cfg = self.cfg.instantiate()
        self.experiment = self.cfg.Experiment

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
        try:
            brickDo = template.render({'brick': TemplateBrick(brick)})
        except:
            logging.exception("Error while rendering Brick %s" % brick.path)
            raise

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

        # TODO: move to self
        brick.fsCreateSymlinks(brick.symlinks())
        self.generateRedoFile(brick)

        if 'parts' in brick:
            for part in brick.parts.keys():
                self.generateBricks(brick.parts[part])


def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', help='Setup config file included as $Setup.', default=None)
    parser.add_argument('-v', '--verbose', help='Verbose mode for debugging.', action='store_true')
    parser.add_argument('config', help='Root Experiment config file.', nargs='?', default='experiment.cfg')
    return parser.parse_args()

if __name__ == '__main__':
    args = parseArguments()

    logLevel = logging.DEBUG if args.verbose else logging.ERROR
    gen = ConfigGenerator(args.config, args.setup, logLevel)
    gen.instantiate()
    gen.generateBricks(gen.experiment)

    # create convenience default.do file
    shutil.copy(os.path.join(gen.appDir, 'bricks/default.do'), os.getcwd())

    sys.stderr.write('Now run the experiment using redo\n')
