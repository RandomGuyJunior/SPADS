import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("catalog_lookup", Path(__file__).with_name("mod-catalog-lookup.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.mods = [
            {"id": "underwater-afus", "name": "Underwater Advanced Fusion", "rapid_tag": "dev-mods:underwater-afus", "enabled": True},
            {"id": "off", "name": "Disabled Mod", "rapid_tag": "dev-mods:off", "enabled": False},
        ]

    def test_catalogue_id(self):
        self.assertEqual(len(module.lookup(self.mods, "underwater-afus")), 1)

    def test_name_casefold(self):
        self.assertEqual(len(module.lookup(self.mods, "UNDERWATER ADVANCED FUSION")), 1)

    def test_rapid_tag(self):
        self.assertEqual(len(module.lookup(self.mods, "dev-mods:underwater-afus")), 1)

    def test_disabled_hidden(self):
        self.assertEqual(module.lookup(self.mods, "off"), [])

    def test_disabled_explicit(self):
        self.assertEqual(len(module.lookup(self.mods, "off", True)), 1)

    def test_no_partial_match(self):
        self.assertEqual(module.lookup(self.mods, "underwater"), [])


if __name__ == "__main__":
    unittest.main()
