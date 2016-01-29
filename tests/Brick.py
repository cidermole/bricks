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
        Experiment = Brick(self.cfg.Experiment)
        #print(Experiment.parts.Brick2.input.ins[0].path)

        print(Experiment.parts.Brick2.input.ins.data[0])
        print(Experiment.parts.Brick2.input.ins.data[0].path)

        self.assertEqual(Experiment.parts.Brick2.input.ins.data[0].path, 'Experiment.parts.Brick2.input.ins[0]')

    def testPathParts(self):
        Experiment = Brick(self.cfg.Experiment)
        self.assertEqual(Experiment.parts.Brick2.sequence[0].pathParts(), ['Experiment', 'parts', 'Brick2', 'sequence', '0'])
