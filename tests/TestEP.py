from __future__ import print_function

from ConfigTest import ConfigTest
from brick_config import config
import logging



class MiniCfg(ConfigTest):
    def setUp(self):
        #self.setupLogging(logging.DEBUG)
        self.setupLogging(logging.INFO)
        self.setupSearchPath()
        self.setupConfigFile("../examples/mmt/ep_ibm10k.cfg")


class JointWordAlignerListOutput(MiniCfg):
    def testListOutput(self):
        Experiment = self.cfg.Experiment
        self.assertEqual('$parts.Split0.output.texts[0]', str(Experiment.parts.JointWordAligner0.output.alignments.data[0]))
