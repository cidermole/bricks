import logging
import os
import unittest
from StringIO import StringIO
from brick_config import config


class ConfigTest(unittest.TestCase):
    """
    Basic setup for config tests. Sets up logging, Config and
    ConfigSearchPath.
    """

    CONFIG = ""
    # or: CONFIG = {'config1': """Brickname: { ... }"""}

    def setupLogging(self):
        logLevel = logging.INFO
        ch = logging.StreamHandler()
        config.logger.addHandler(ch)
        config.logger.setLevel(logLevel)

    def setupSearchPath(self):
        appDir = os.path.dirname(os.path.realpath(__file__))
        searchPath = os.path.join(*[appDir, '..', 'bricks'])
        assert(os.path.exists(searchPath))
        self.configSearchPath = config.ConfigSearchPath([searchPath])

    def setupConfig(self):
        if type(self.CONFIG) is str:
            # CONFIG is a single configuration str, just create it
            self.cfg = config.Config(StringIO(self.CONFIG), searchPath=self.configSearchPath).instantiate()
        elif type(self.CONFIG) is dict:
            # if CONFIG is dict, create one config per key/value pair
            self.cfg = {}
            for k, c in self.CONFIG:
                self.cfg[k] = config.Config(StringIO(c), searchPath=self.configSearchPath).instantiate()
        else:
            raise ValueError("ConfigTest: CONFIG must be either str or dict.")

    def setupConfigFile(self, fileName, instantiate=True):
        cfg = config.Config(file(fileName), searchPath=self.configSearchPath)

        # can we split this off ConfigGenerator somehow, to avoid duplicate code? (note parent=cfg vs. parent=self.cfg, same in cfg.Setup)
        setupFileName = None
        if setupFileName is None:
            setupFileName = 'Setups/%s.cfg' % os.uname()[1].capitalize()
        # resolve relative path in bricks program root
        setupFileName = self.configSearchPath.searchGlobalFile(setupFileName)
        setup = config.Config(setupFileName, parent=cfg, searchPath=self.configSearchPath)
        # implicit str $BRICKS: path to bricks program root directory
        appDir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # two up: bricks program root
        setup.BRICKS = appDir

        # implicit Mapping $Setup: Experiment can inherit $Setup for machine-specific config keys
        cfg.Setup = setup

        self.cfg = cfg.instantiate() if instantiate else cfg

    def setUp(self):
        self.setupLogging()
        self.setupSearchPath()
        self.setupConfig()
