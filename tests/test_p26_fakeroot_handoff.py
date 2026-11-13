"""Regression for ownership metadata persistence across fakeroot processes."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("fakeroot"), "fakeroot unavailable")
class FakerootHandoffTest(unittest.TestCase):
    def test_saved_state_restores_package_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shadow = root / "shadow"
            state = root / "fakeroot.state"
            shadow.write_text("root:!:0:0:99999:7:::\n")
            # Nonzero target IDs distinguish preserved metadata from the
            # host's default ownership. Never infer target IDs from host stat.
            subprocess.run(
                ["fakeroot", "-s", str(state), "--", "chown", "123:456", str(shadow)],
                check=True,
            )
            self.assertTrue(state.is_file())
            result = subprocess.run(
                ["fakeroot", "-i", str(state), "--", "stat", "-c", "%u:%g", str(shadow)],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(result.stdout.strip(), "123:456")


if __name__ == "__main__":
    unittest.main()
