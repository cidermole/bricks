#!/usr/bin/env python2

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
        path = [part for part in configPath if part != "parts"]
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
                return os.path.join(*(['..', '..'] + relativePath[2:4]))

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
                return None

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
            elif type(inp) is str:
                # a direct filename specification.
                #sys.stderr.write("STR %s\n" % inp)
                linkSource = inp

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

class ConfigGenerator(object):
    def __init__(self, cfg):
        self.experiment = cfg.Experiment.copyExceptRefs(cfg, 'Experiment')
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath='.'))

    def generateRedoFile(self, brick):
        """
        Generate a redo file from template for this Brick.
        """
        template = self.env.get_template('brick.do.jinja')
        brickDo = template.render({
            # all the Bricks we depend on
            'inputDependencies': list(brick.inputDependencies()),
            'outputDependencies': list(brick.outputDependencies()),

            'brick': brick.path
        })
        with open(os.path.join(brick.filesystemPath(), 'brick.do'), 'w') as fo:
            fo.write(brickDo)

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
        self.generateRedoFile(brick)

        if 'parts' in brick:
            for part in brick.parts:
                self.generateBricks(brick.parts[part])


if __name__ == '__main__':
    cfg = config.Config(file('global.cfg'))
    gen = ConfigGenerator(cfg)
    gen.generateBricks(gen.experiment)
