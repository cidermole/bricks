from ConfigTest import ConfigTest
from brick_config import config
from bricks import Brick


class BrickDependency(ConfigTest):
    CONFIG = """
    Experiment: {
      input: {}
      output: {}
    }
    """

    def testInputDependencies(self):
        brick = Brick(self.cfg.Experiment)


#class BrickWiring(ConfigTest):
class ConfigPaths(ConfigTest):
    def setUp(self):
        self.setupLogging()
        self.setupSearchPath()
        self.setupConfigFile("debug.cfg")

    def testInputDependencies(self):
        Experiment = Brick(self.cfg.Experiment)

        #print(Experiment.parts.Brick2.input.ins.data[0])
        #print(Experiment.parts.Brick2.input.ins.data[0].path)

        self.assertEqual(
            Experiment.parts.Brick2.input.ins.data[0].path,
            'Experiment.parts.Brick2.input.ins[0]'
        )

    def testPathParts(self):
        Experiment = Brick(self.cfg.Experiment)
        self.assertEqual(
            Experiment.parts.Brick2.sequence[0].pathParts(),
            ['Experiment', 'parts', 'Brick2', 'sequence', '0']
        )


class ConfigRelativePaths(ConfigTest):
    def setUp(self):
        self.setupLogging()
        self.setupSearchPath()
        self.setupConfigFile("debug.cfg")

    def testExperimentCasesAI(self):
        Experiment = self.cfg.Experiment
        self.assertEqual(
            Experiment.output.data['out'].relativePath(Experiment.output),
            '_.parts.Brick2.output.out'.split('.')
        )
        self.assertEqual(
            Experiment.output.data['out2'].relativePath(Experiment.output),
            # ['_', 'parts', 'Brick2', 'output', 'outs', '0']
            '_.parts.Brick2.output.outs.0'.split('.')
        )

    def testBrick1CaseB(self):
        Experiment = self.cfg.Experiment
        Brick1 = Experiment.parts.Brick1
        self.assertEqual(
            Brick1.input.data['in'].relativePath(Brick1.input),
            '_._._.input.in'.split('.')
        )

    def testBrick2CasesCDG(self):
        Experiment = self.cfg.Experiment
        Brick2 = Experiment.parts.Brick2
        self.assertEqual(
            Brick2.input.data['in'].relativePath(Brick2.input),
            '_._.Brick1.output.out'.split('.')
        )
        self.assertEqual(
            # note: resolves from within the input Sequence
            Brick2.input.ins.data[0].relativePath(Brick2.input.ins),
            '_._._.Brick1.output.out'.split('.')
        )
        self.assertEqual(
            # note: resolves from within the input Sequence
            Brick2.input.inp.data[0].relativePath(Brick2.input.inp),
            '_._._._.input.in'.split('.')
        )

    def testSub1CaseJ(self):
        Experiment = self.cfg.Experiment
        Sub1 = Experiment.parts.Brick2.parts.Sub1
        self.assertEqual(
            Sub1.input.data['in2'].relativePath(Sub1.input),
            '_._._.input.ins.0'.split('.')
        )

    def testBrick3CaseH(self):
        Experiment = self.cfg.Experiment
        Brick3 = Experiment.parts.Brick3
        self.assertEqual(
            Brick3.input.data['in'].relativePath(Brick3.input),
            '_._.Brick2.output.outs.0'.split('.')
        )
