import bricks
from brick_config import config
from StringIO import StringIO
import logging
import os
import unittest
from ConfigTest import ConfigTest


class OverrideMapping(ConfigTest):
    CONFIG = """
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

    def test_inherits(self):
        """
        Tests basic inheritance of Base.mapping into Derived.
        """
        self.assertTrue('mapping' in self.cfg.Derived, "Derived.mapping should be inherited.")
