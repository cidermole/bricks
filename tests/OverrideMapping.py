from ConfigTest import ConfigTest


class InheritMapping(ConfigTest):
    CONFIG = """
    Base: {
      mapping: {
        a: apples
        b: bananas
      }
    }

    Derived: {
      extends: $Base
    }
    """

    def testInherits(self):
        self.assertTrue('mapping' in self.cfg.Derived, "Derived.mapping should be inherited from Base.mapping")
        self.assertTrue('a' in self.cfg.Derived.mapping, "Derived.mapping.a should be inherited from Base.mapping.a")
        self.assertTrue('b' in self.cfg.Derived.mapping, "Derived.mapping.b should be inherited from Base.mapping.b")

    def testMappingValue(self):
        self.assertEqual(self.cfg.Derived.mapping.a, 'apples', "Derived.mapping.a should be inherited from Base.mapping.a")
        self.assertEqual(self.cfg.Derived.mapping.b, 'bananas', "Derived.mapping.b should be inherited from Base.mapping.b")


class OverrideMapping(ConfigTest):
    CONFIG = """
    Base: {
      mapping: {
        a: apples
        b: bananas
      }
    }

    DerivedEmpty: {
      extends: $Base
      mapping: {}
    }

    Derived: {
      extends: $Base
      mapping: {
        a: apricot
        b: blackberry
      }
    }
    """

    def testInheritsNot(self):
        self.assertTrue('mapping' in self.cfg.DerivedEmpty, "DerivedEmpty.mapping should exist")
        self.assertFalse('a' in self.cfg.DerivedEmpty.mapping, "DerivedEmpty.mapping.a should not be inherited from Base.mapping.a")
        self.assertFalse('b' in self.cfg.DerivedEmpty.mapping, "DerivedEmpty.mapping.b should not be inherited from Base.mapping.b")

    def testMappingPresent(self):
        self.assertTrue('mapping' in self.cfg.Derived, "Derived.mapping should exist")
        self.assertEqual(self.cfg.Derived.mapping.a, 'apricot', "Derived.mapping.a should not be inherited from Base.mapping.a")
        self.assertEqual(self.cfg.Derived.mapping.b, 'blackberry', "Derived.mapping.b should not be inherited from Base.mapping.b")
