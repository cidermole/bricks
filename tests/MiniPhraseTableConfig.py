from ConfigTest import ConfigTest


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
