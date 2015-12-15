from ConfigTest import ConfigTest
from brick_config import config


class MiniPhraseTableConfig(ConfigTest):
    def setUp(self):
        self.setupLogging()
        self.setupSearchPath()
        self.setupConfigFile("examples/mini.cfg")

    def testInherits(self):
        self.assertTrue('phraseTable' in self.cfg.Experiment.parts.DevTables0)
        self.assertTrue('numPhraseFeatures' in self.cfg.Experiment.parts.DevTables0)

    def testParentValue(self):
        self.assertEqual(self.cfg.Experiment.parts.PhraseTable0.numPhraseFeatures, 4)

    def testInheritedValue(self):
        self.assertEqual(self.cfg.Experiment.parts.DevTables0.numPhraseFeatures, 4)

    # elaborate further on the failure of testInheritedValue()

    def testReference(self):
        # bug: this Reference should not have been resolved when copying in instantiate()
        numPhraseFeatures = self.cfg.Experiment.parts.DevTables0.data['numPhraseFeatures']
        self.assertEqual(type(numPhraseFeatures), config.Reference)

    def testParentReference(self):
        # but surely, the parent itself still has it as a reference?
        numPhraseFeatures = self.cfg.Bricks.Phrase.Post.FilterBinarizeTables.data['numPhraseFeatures']
        self.assertEqual(type(numPhraseFeatures), config.Reference)

        # .parts.BinarizeReorderingTable0

    def testParentIdentity(self):
        parentPath = self.cfg.Bricks.Phrase.Post.FilterBinarizeTables.path
        self.assertEqual(parentPath, 'Bricks.Phrase.Post.FilterBinarizeTables')

    def testConfigObjectData(self):
        """Why this? AttributeError: 'Config' object has no attribute 'data'"""
        # bug: instantiate() did not properly copy this Config
        Bricks = self.cfg.Bricks
        Phrase = Bricks.Phrase  # fails here
        parentPath = Phrase.Post.FilterBinarizeTables.path
        self.assertEqual(parentPath, 'Bricks.Phrase.Post.FilterBinarizeTables')


class MiniPhraseTableConfigNoInstantiate(ConfigTest):
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
