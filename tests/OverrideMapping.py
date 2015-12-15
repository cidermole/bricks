import bricks
from brick_config import config
import logging
import os
import unittest

OVERRIDE_MAPPING = """
Base: {
  mapping: {
    key1: apples
    key2: bananas
  }
}

Derived: {
  extends: $Base
}
"""

class OverrideMapping(unittest.TestCase):
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
        self.cfg = config.Config(OVERRIDE_MAPPING, searchPath=configSearchPath).instantiate()

    def setUp(self):
        self.setupLogging()
        self.setupConfig()

    def test_inherits(self):
        self.assertEqual('foo'.upper(), 'FOO')
