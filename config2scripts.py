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

    def referenceDependencyPath(self, relativePath):
        """
        Turns a config path referencing another Brick into a filesystem path
        for adding dependencies to the runner system.
        """

        # currently we only support dependencies of the form:
        # ['_', '_', 'Giza12', 'output', 'alignment']
        #print(relativePath)
        if len(relativePath) == 5 and relativePath[0:2] == ['_', '_'] \
                and relativePath[3] == 'output':
            return os.path.join('..', relativePath[2], 'brick')

        return None

    def inputDependencies(self):
        """
        Get all Bricks which we depend on, as a list of relative
        file paths for the runner system.
        """
        dependencies = set()

        for (key, inp) in self.input.data.iteritems():
            if type(inp) is config.Reference:
                relPath = inp.relativePath(self.input)
                dependencyPath = self.referenceDependencyPath(relPath)
                if dependencyPath is not None:
                    dependencies.add(dependencyPath)
            elif type(inp) is str:
                # check if file exists in FS
                # TODO: relative paths?
                if not os.path.exists(inp):
                    raise ValueError("input %s of Brick %s = %s does not exist in file system." % (key, self.path, inp))
            elif type(inp) is bool:
                raise ValueError("input %s of Brick %s is neither connected nor defined." % (key, self.path))

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
        print(brick.inputDependencies())

        if 'parts' in brick:
            for part in brick.parts:
                self.generateBricks(brick.parts[part])


if __name__ == '__main__':
    cfg = config.Config(file('global.cfg'))
    #e = cfg.Experiment.copyExceptRefs(cfg, 'Experiment')
    gen = ConfigGenerator(cfg)
    gen.generateBricks(gen.experiment)
