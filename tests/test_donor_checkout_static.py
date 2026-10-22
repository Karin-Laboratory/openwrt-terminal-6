import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class DonorStaticTests(unittest.TestCase):
    def test_commit_pinned(self):
        script = (ROOT / "scripts/fetch-donor-source.sh").read_text()
        self.assertIn("a40df9a5afb46716dea799acea69f17480df4d82", script)
        self.assertIn("checkout --detach", script)

    def test_no_build_or_flash_actions(self):
        script = (ROOT / "scripts/fetch-donor-source.sh").read_text()
        self.assertNotIn("\nmake ", script)
        self.assertNotIn("\ndd ", script)
        self.assertNotIn("\nfastboot ", script)

if __name__ == "__main__":
    unittest.main()
