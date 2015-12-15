from ConfigTest import ConfigTest


class Inherit(ConfigTest):
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


class Override(ConfigTest):
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
        self.assertEqual(self.cfg.Derived.mapping.a, 'apricot')  # "Derived.mapping.a should not be inherited from Base.mapping.a"
        self.assertEqual(self.cfg.Derived.mapping.b, 'blackberry')  # "Derived.mapping.b should not be inherited from Base.mapping.b"


class OverrideInherit(ConfigTest):
    CONFIG = """
    Derived: {
      extends: $Base
      mapping: { key: value }
    }

    Base: {
      key: $mapping.key
    }
    """

    def testInherits(self):
        self.assertTrue('key' in self.cfg.Derived, "Derived.key should be inherited from Base.key")
        self.assertFalse('mapping' in self.cfg.Base, "Base.mapping should not be defined")

    def testReference(self):
        self.assertEqual(self.cfg.Derived.key, 'value')  # "Derived.key should get the referenced, inherited value from Derived.mapping.key"


class ReferenceInherit(ConfigTest):
    CONFIG = """
    Derived: {
      extends: $Base
      mapping: { key: newValue }
    }

    Base: {
      key: $mapping.key
      mapping: { key: oldValue }
    }
    """

    def testInherits(self):
        self.assertTrue('key' in self.cfg.Derived, "Derived.key should be inherited from Base.key")
        self.assertTrue('mapping' in self.cfg.Base, "Base.mapping should be defined")
        self.assertEqual(self.cfg.Base.mapping.key, 'oldValue')  # "Base.mapping.key should stay unchanged"

    def testReference(self):
        self.assertEqual(self.cfg.Derived.key, 'newValue')  # "Derived.key should get the referenced, inherited value from Derived.mapping.key"
