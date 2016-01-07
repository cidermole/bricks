from ConfigTest import ConfigTest
from brick_config import config
from bricks import Brick


class BrickDependencyTest(ConfigTest):
    CONFIG = """
    Experiment: {
      # a
    }
    """

    def testInputDependencies(self):
        brick = Brick(self.cfg.Experiment)
