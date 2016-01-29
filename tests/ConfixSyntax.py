from ConfigTest import ConfigTest
import logging


class FunctionSyntax(ConfigTest):
    CONFIG = """
    i: 1

    val: ${str($i)}

    s: "hello "
    s2: $s + $val
    """

    def setUp(self):
        #self.setupLogging(logging.DEBUG)
        self.setupLogging(logging.INFO)
        self.setupSearchPath()
        self.setupConfig()

    def testFunctionSyntax(self):
        self.assertEqual('hello 1', self.cfg.s2)
