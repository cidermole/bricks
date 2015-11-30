#!/usr/bin/env python2

from __future__ import print_function

import config
import os


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

    def filesystemPath(self):
        """
        Map the config path to a relative filesystem path of the experiment
        directory which will contain this Brick's data for the runner system.
        """
        # replace .parts: shortens "Experiment.parts.WordAligner0.parts.Giza12"
        # into "Experiment.WordAligner0.Giza12"
        path = [part for part in self.path.split('.') if part != "parts"]
        return os.path.join(path)

    def referenceDependencyPath(self, relativePath):
        """
        Turns a config path referencing another Brick into a filesystem path.
        Used for adding dependencies to the runner system.
        """
        #print(relativePath)

        # currently we only support dependencies of the form ...:

        # ['_', '_', 'Giza12', 'output', 'alignment']
        # used for input dependencies
        if len(relativePath) == 5 and relativePath[0:2] == ['_', '_'] \
                and relativePath[3] == 'output':
            return os.path.join('..', relativePath[2], 'brick')

        # ['_', 'parts', 'WordAligner0', 'output', 'alignment']
        # used for output dependencies
        if len(relativePath) == 5 and relativePath[0:2] == ['_', 'parts'] \
                and relativePath[3] == 'output':
            return os.path.join(relativePath[2], 'brick')

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
                # TODO: relative paths?
                if not os.path.exists(inp):
                    raise ValueError("input %s of Brick %s = %s does not exist in file system." % (key, self.path, inp))
            elif type(inp) is bool:
                # no specification at all, e.g. input: { src }
                # here, config parser falls back to defining a bool src=True
                raise ValueError("input %s of Brick %s is neither connected nor defined as a file." % (key, self.path))

        return dependencies

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

    def generateBricks(self, cfgBrick):
        """
        Recursively generate a config for this Brick and all
        its parts.
        """
        # we know / assume that this brick is a Brick.
        print('Brick %s...' % cfgBrick.path)
        brick = Brick(cfgBrick)
        if len(brick.inputDependencies()) > 0:
            print('input', brick.inputDependencies())
        if len(brick.outputDependencies()) > 0:
            print('output', brick.outputDependencies())

        if 'parts' in brick:
            for part in brick.parts:
                self.generateBricks(brick.parts[part])


if __name__ == '__main__':
    cfg = config.Config(file('global.cfg'))
    #e = cfg.Experiment.copyExceptRefs(cfg, 'Experiment')
    gen = ConfigGenerator(cfg)
    gen.generateBricks(gen.experiment)
