import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("rapid_lookup", Path(__file__).with_name("mod-catalog-lookup.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

REPOS = "randomguy-hosting,https://randomguyrapid.duckdns.org/randomguy-hosting,,\nmodded-chobby,https://randomguyrapid.duckdns.org/modded-chobby,,\n"
VERSIONS = "randomguy-hosting:test,abc123,RandomGuy Hosting,test-154\nrandomguy-hosting:stable,def456,RandomGuy Hosting,stable\n"


def fake_fetch(url):
    if url.endswith("/repos.gz"):
        return REPOS
    if url.endswith("/randomguy-hosting/versions.gz"):
        return VERSIONS
    if url.endswith("/modded-chobby/versions.gz"):
        return ""
    raise AssertionError(f"Unexpected request: {url}")


class RapidLookupTests(unittest.TestCase):
    def test_published(self):
        self.assertEqual(module.find_tag("randomguy-hosting:test", fetch=fake_fetch), VERSIONS.splitlines()[0])

    def test_unpublished(self):
        self.assertIsNone(module.find_tag("randomguy-hosting:missing", fetch=fake_fetch))

    def test_unknown_repo(self):
        self.assertIsNone(module.find_tag("unknown:test", fetch=fake_fetch))

    def test_exact_match(self):
        self.assertIsNone(module.find_tag("randomguy-hosting:tes", fetch=fake_fetch))

    def test_invalid_tag(self):
        with self.assertRaises(ValueError):
            module.find_tag("not-a-tag", fetch=fake_fetch)

    def test_network_failure_is_not_missing(self):
        def fail(url):
            raise OSError("network offline")
        with self.assertRaises(OSError):
            module.find_tag("randomguy-hosting:test", fetch=fail)


if __name__ == "__main__":
    unittest.main()
