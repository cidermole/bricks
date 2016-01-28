#!/usr/bin/env python
from __future__ import print_function

from collections import namedtuple
import logging
import subprocess


Score = namedtuple("Score", ["bleu", "bleu_sel_var", "bleu_opt_var", "meteor", "meteor_sel_var", "meteor_opt_var", "ter", "ter_sel_var", "ter_opt_var"])


class MultEval:
    """
    Wrapper around https://github.com/jhclark/multeval
    "Better Hypothesis Testing for Statistical Machine Translation: Controlling for Optimizer Instability" from ACL 2011.
    http://www.cs.cmu.edu/~jhclark
    """
    def __init__(self, reference, targetLang, multeval='multeval.sh', logger=None):
        """
        :param reference:  reference sentences file
        :param targetLang: target language 2-letter code
        :param multeval:   /optional/path/to/multeval.sh
        :param logger      optional logger
        """
        self.logger = logger or logging.getLogger('dummy')
        self.reference, self.targetLang = reference, targetLang
        self.multeval = multeval

    def run(self, hyps):
        """
        :param hyps: list of hypothesis files with one sentence per line
        :return: Score with BLEU, METEOR and TER scores (in strings each)
        """
        cmd = [self.multeval, 'eval', '--refs', self.reference, '--hyps-baseline'] + hyps + ['--meteor.language', self.targetLang]
        self.logger.debug("Running %s" % ' '.join(cmd))
        output = subprocess.check_output(cmd)
        return MultEval.parseOutput(output)

    @staticmethod
    def parseOutput(output):
        # thanks for the parser, Barry
        for line in output.split("\n"):
            if not line.startswith("baseline"):
                continue
            fields = line.split()
            bleu = fields[1]
            bleu_sel_var, bleu_opt_var, _ = fields[2][1:-1].split("/")
            meteor = fields[3]
            meteor_sel_var, meteor_opt_var, _ = fields[4][1:-1].split("/")
            ter = fields[5]
            ter_sel_var, ter_opt_var, _ = fields[6][1:-1].split("/")
            scores = Score(bleu, bleu_sel_var, bleu_opt_var, meteor, meteor_sel_var, meteor_opt_var, ter,
                           ter_sel_var, ter_opt_var)
            return scores
        return None

# test parser if this file is run directly.
if __name__ == '__main__':
    example_multeval_output = '''n=5            BLEU (s_sel/s_opt/p)   METEOR (s_sel/s_opt/p) TER (s_sel/s_opt/p)    Length (s_sel/s_opt/p)
baseline       28.0 (0.3/0.0/-)       32.7 (0.2/0.0/-)       52.3 (0.3/0.0/-)       95.7 (0.3/0.1/-)
'''

    print(MultEval.parseOutput(example_multeval_output))
