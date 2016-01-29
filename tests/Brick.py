from ConfigTest import ConfigTest
from brick_config import config
from bricks import Brick


class BrickDependencyTest(ConfigTest):
    CONFIG = """
    Experiment: {
      input: {}
      output: {}
    }
    """

    def testInputDependencies(self):
        brick = Brick(self.cfg.Experiment)


class BrickWiringTest(ConfigTest):
    def setUp(self):
        self.setupLogging()
        self.setupSearchPath()
        self.setupConfigFile("debug.cfg")

    def testInputDependencies(self):
        brick = Brick(self.cfg.Experiment)
