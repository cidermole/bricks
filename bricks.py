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
# The idea for incremental experiments will be to check via 'redo' if targets
# need to be run, and if they don't, we can symlink their input back to the
# previous run.
#

from __future__ import print_function

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
        configPath = configPath.split('.')
        path = ['0']
        path += [part for part in configPath if part != "parts"]
        return os.path.join(*path)

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
                return os.path.join(*(['..', '..'] + relativePath[2:5]))

        # ['_', '_', '_', 'input', 'src']
        # used in referencing the Brick's input in parts
        if len(relativePath) == 5 and relativePath[0:3] == ['_', '_', '_'] \
                and relativePath[3] in ['output', 'input']:
            if brickOnly:
                return None
            else:
                return os.path.join(*(['..', '..'] + relativePath[3:5]))

        # ['_', 'parts', 'WordAligner0', 'output', 'alignment']
        # used for output dependencies
        if len(relativePath) == 5 and relativePath[0:2] == ['_', 'parts'] \
                and relativePath[3] == 'output':
            if brickOnly:
                return os.path.join(relativePath[2], 'brick')
            else:
                return os.path.join(*(['..'] + relativePath[2:5]))

        return None

    def inputDependencies(self):
        """
        Get all Bricks which we depend on, as a list of relative
        file paths for the runner system.
        """
        dependencies = set()

        # walk this Brick's inputs without resolving config keys
        for (key, inp) in self.input.data.iteritems():
            if type(inp) is config.Reference:
                # we may be referencing another Brick, which we then
                # need to add as a dependency.
                relPath = inp.relativePath(self.input)
                path = self.referenceDependencyPath(relPath)
                if path is not None:
                    dependencies.add(path)
            elif type(inp) is str:
                # a direct filename specification.
                # check if file exists in FS
                if not os.path.exists(inp):
                    raise ValueError("input %s of Brick %s = %s does not exist in file system." % (key, self.path, inp))
            elif type(inp) is bool:
                # no specification at all, e.g. input: { src }
                # here, config parser falls back to defining a bool src=True
                raise ValueError("input %s of Brick %s is neither connected nor defined as a file." % (key, self.path))

        return dependencies

    def createInputSymlinks(self):
        """
        Create symlinks for all inputs.
        """
        fsPath = self.filesystemPath()

        # walk this Brick's inputs without resolving config keys
        for (key, inp) in self.input.data.iteritems():
            linkSource = None
            if type(inp) is config.Reference:
                # referencing another Brick
                #linkSource = self.filesystemPath(inp.path)
                relPath = inp.relativePath(self.input)
                linkSource = self.referenceDependencyPath(relPath, brickOnly=False)
            #elif type(inp) is str:
            else:
                # str, or config.Expression
                # a direct filename specification.
                #sys.stderr.write("STR %s\n" % inp)

                # potentially resolve config.Expression
                linkSource = self.input[key]

            if linkSource is not None:
                linkTarget = os.path.join(fsPath, 'input', key)
                #sys.stderr.write("%s -> %s\n" % (linkSource, linkTarget))

                if not os.path.exists(os.path.dirname(linkTarget)):
                    os.makedirs(os.path.dirname(linkTarget))
                if os.path.islink(linkTarget):
                    os.unlink(linkTarget)
                os.symlink(linkSource, linkTarget)

    def outputDependencies(self):
        """
        Get all our Bricks (parts) which produce our output.
        In practice, this should only be necessary for Experiment itself.
        """
        dependencies = set()

        # walk this Brick's outputs without resolving config keys
        for (key, outp) in self.output.data.iteritems():
            if type(outp) is config.Reference:
                # we may be referencing another Brick, which we then
                # need to add as a dependency.
                relPath = outp.relativePath(self.output)
                path = self.referenceDependencyPath(relPath)
                if path is not None:
                    dependencies.add(path)
            elif type(outp) is bool:
                # no specification at all, e.g. output: { trg }
                # here, config parser falls back to defining a bool trg=True
                # (not an output dependency)
                pass

        return dependencies

    def createOutputSymlinks(self):
        """
        Create symlinks for all outputs.
        """
        # TODO: almost equivalent with createInputSymlinks()
        # TODO: unify!
        fsPath = self.filesystemPath()

        # walk this Brick's outputs without resolving config keys
        for (key, outp) in self.output.data.iteritems():
            #print("key:", key, type(outp), self.path)
            linkSource = None
            if type(outp) is config.Reference:
                # referencing another Brick
                relPath = outp.relativePath(self.output)
                linkSource = self.referenceDependencyPath(relPath, brickOnly=False)
            # TODO: divergence here, below.
            elif type(outp) is bool:
                # linking bool to itself??
                # e.g. Experiment.parts.WordAligner0.parts.GizaPrepare
                # "True -> 0/Experiment/WordAligner0/GizaPrepare/output/preparedCorpusDir"
                continue
            # TODO: end divergence.
            else:
                # str, or config.Expression
                # a direct filename specification.
                #sys.stderr.write("STR %s\n" % inp)

                # potentially resolve config.Expression
                linkSource = self.output[key]

            if linkSource is not None:
                linkTarget = os.path.join(fsPath, 'output', key)
                sys.stderr.write("%s -> %s\n" % (linkSource, linkTarget))

                # TODO: also, linking output, we just need one ../
                # e.g. WordAligner0/output/alignment -> ../Symmetrizer0/output/alignment
                if not os.path.exists(os.path.dirname(linkTarget)):
                    os.makedirs(os.path.dirname(linkTarget))
                if os.path.islink(linkTarget):
                    os.unlink(linkTarget)
                os.symlink(linkSource, linkTarget)



class ConfigGenerator(object):
    def __init__(self, cfgFileName, searchPath):
        configSearchPath = config.ConfigSearchPath([searchPath])
        cfg = config.Config(file(cfgFileName), searchPath=configSearchPath)
        self.experiment = cfg.Experiment.copyExceptRefs(cfg, 'Experiment')
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
        brickDo = template.render({
            'brick': brick

            # convenience strings. Maybe shortest to hardcode instead
            # (symlinks ensure correctness anyway).
            #'input': {k: 'input/%s' % k for k in brick.input.data.keys()},
            #'output': {k: 'output/%s' % k for k in brick.output.data.keys()}
        })

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
        sys.stderr.write('%s\n' % cfgBrick.path)
        if len(brick.inputDependencies()) > 0:
            sys.stderr.write('  input %s\n' % str(brick.inputDependencies()))
        if len(brick.outputDependencies()) > 0:
            sys.stderr.write('  output %s\n' % str(brick.outputDependencies()))

        brick.createInputSymlinks()
        brick.createOutputSymlinks()
        self.generateRedoFile(brick)

        if 'parts' in brick:
            for part in brick.parts:
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
