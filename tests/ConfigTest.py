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

    def setupLogging(self):
        logLevel = logging.INFO
        ch = logging.StreamHandler()
        config.logger.addHandler(ch)
        config.logger.setLevel(logLevel)

    def setupConfig(self):
        appDir = os.path.dirname(os.path.realpath(__file__))
        searchPath = os.path.join(*[appDir, '..', 'bricks'])
        assert(os.path.exists(searchPath))

        configSearchPath = config.ConfigSearchPath([searchPath])
        self.cfg = config.Config(StringIO(self.CONFIG), searchPath=configSearchPath).instantiate()

    def setUp(self):
        self.setupLogging()
        self.setupConfig()
