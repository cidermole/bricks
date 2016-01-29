from ConfigTest import ConfigTest


class SimpleOutputList(ConfigTest):
    """
    This config works because the config parser can statically determine
    the length of the input list.
    """

    CONFIG = """
    Brick: {
      input:  { sources: [ "/tmp/1", "/tmp/2" ] }
      output: { alignments: [ True | i: [0..$input.sources.length-1] ] }
    }
    """

    def testOutputList(self):
        Brick = self.cfg.Brick
        self.assertEqual(Brick.output.data['alignments']['length'], 2)


class InheritOutputList(ConfigTest):
    """
    This should be possible by lazy evaluation.
    """
    CONFIG = """
    Base: {
      input:  { sources: [] }
      output: { alignments: [ True | i: [0..$input.sources.length-1] ] }
    }

    Derived: {
      extends: $Base
      input:  { sources: [ "/tmp/1", "/tmp/2" ] }
    }
    """

    def testOutputList(self):
        Derived = self.cfg.Derived
        # this fails, because the parser evaluates the "list comprehension" [0..$var] statically.
        # hence, it fails to work with inheritance.
        self.assertEqual(Derived.output.data['alignments']['length'], 2)

        # a lazy Sequence has a dynamic length not determined at parse time
        # we will still parse the body once, but only statically (avoids parse errors).
