from ConfigTest import ConfigTest
from brick_config import config


class MiniCfg(ConfigTest):
    def setUp(self):
        self.setupLogging()
        self.setupSearchPath()
        self.setupConfigFile("examples/mini.cfg")


class InheritMapping(MiniCfg):
    def testInherits(self):
        self.assertTrue('phraseTable' in self.cfg.Experiment.parts.DevTables0)
        self.assertTrue('numPhraseFeatures' in self.cfg.Experiment.parts.DevTables0)

    def testParentValue(self):
        self.assertEqual(self.cfg.Experiment.parts.PhraseTable0.numPhraseFeatures, 4)

    def testInheritedValue(self):
        self.assertEqual(self.cfg.Experiment.parts.DevTables0.phraseTable.numPhraseFeatures, 4)

    # elaborate further on the failure of testInheritedValue()

    def testReference(self):
        numPhraseFeatures = self.cfg.Experiment.parts.DevTables0.phraseTable.data['numPhraseFeatures']
        self.assertEqual(type(numPhraseFeatures), config.Reference)

    def testParentReference(self):
        # but surely, the parent itself still has it as a reference?
        # oh wait, nah. That is not where things come from.
        numPhraseFeatures = self.cfg.Bricks.Phrase.Post.FilterBinarizeTables.data['numPhraseFeatures']
        #self.assertEqual(type(numPhraseFeatures), config.Reference)

        # .parts.BinarizeReorderingTable0

    def testParentIdentity(self):
        parentPath = self.cfg.Bricks.Phrase.Post.FilterBinarizeTables.path
        self.assertEqual(parentPath, 'Bricks.Phrase.Post.FilterBinarizeTables')


class InstantiateConfig(MiniCfg):
    def testConfigObjectData(self):
        """Why this? AttributeError: 'Config' object has no attribute 'data'"""
        # fixed bug: instantiate() did not properly copy this Config
        Bricks = self.cfg.Bricks  # fails here
        # in fact, self.cfg doesn't have a data key either!
        Phrase = Bricks.Phrase
        parentPath = Phrase.Post.FilterBinarizeTables.path
        self.assertEqual(parentPath, 'Bricks.Phrase.Post.FilterBinarizeTables')

    def testConfigIncludeType(self):
        # include
        self.assertEqual(type(self.cfg.data['Bricks']), config.Config)
        self.assertEqual(id(self.cfg.Bricks.parent), id(self.cfg))
        # include from include
        self.assertEqual(type(self.cfg.Bricks.data['Phrase']), config.Config)
        self.assertEqual(id(self.cfg.Bricks.Phrase.parent), id(self.cfg.Bricks))


class NoInstantiate(ConfigTest):
    def setUp(self):
        self.setupLogging()
        self.setupSearchPath()
        # instantiate=False -> no inheritance, just the plain config file
        self.setupConfigFile("examples/mini.cfg", instantiate=False)

    def testConfigObjectData(self):
        """Why this? AttributeError: 'Config' object has no attribute 'data'"""
        Bricks = self.cfg.Bricks
        Phrase = Bricks.Phrase
        parentPath = Phrase.Post.FilterBinarizeTables.path
        #self.assertEqual(parentPath, 'Bricks.Phrase.Post.FilterBinarizeTables')

        # flatness: path is relative to Config, which is in its own file!
        self.assertEqual(parentPath, 'FilterBinarizeTables')

    def testConfigIncludeType(self):
        # include
        self.assertEqual(type(self.cfg.data['Bricks']), config.Config)
        self.assertEqual(id(self.cfg.Bricks.parent), id(self.cfg))
        # include from include
        self.assertEqual(type(self.cfg.Bricks.data['Phrase']), config.Config)
        self.assertEqual(id(self.cfg.Bricks.Phrase.parent), id(self.cfg.Bricks))
