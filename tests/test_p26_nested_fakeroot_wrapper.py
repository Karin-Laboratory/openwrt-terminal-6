"""Host regression tests for the native p26 nested-fakeroot wrapper.

Extract the actual embedded script from the workflow rather than testing a copy.
No OpenWrt build, privileged operations, or firmware inputs are required.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/mt6990-native-subtarget.yml"
START = "          cat > \"$host_fakeroot\" <<'FAKEROOT_WRAPPER'\n"
END = "          FAKEROOT_WRAPPER\n"


class NestedFakerootWrapperTests(unittest.TestCase):
    def setUp(self):
        source = WORKFLOW.read_text()
        self.assertEqual(source.count(START), 1)
        script = source.split(START, 1)[1].split(END, 1)[0]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.wrapper = Path(self.temp.name) / "fakeroot"
        self.wrapper.write_text("\n".join(
            line.removeprefix("          ") for line in script.splitlines()
        ) + "\n")
        self.wrapper.chmod(0o755)
        original = Path(str(self.wrapper) + ".original")
        original.write_text("#!/bin/sh\nprintf 'ORIGINAL:%s\\n' \"$*\"\n")
        original.chmod(0o755)

    def invoke(self, *args, nested=True):
        env = os.environ.copy()
        env.pop("FAKEROOTKEY", None)
        if nested:
            env["FAKEROOTKEY"] = "test-only"
        return subprocess.run(
            [str(self.wrapper), *args], env=env,
            text=True, capture_output=True, check=False,
        )

    def test_nested_command_preserves_arguments(self):
        result = self.invoke("--", "/bin/echo", "PASS", "with spaces")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "PASS with spaces\n")

    def test_nested_state_options_are_consumed(self):
        result = self.invoke("-i", "input.state", "-s", "output.state",
                             "--", "/bin/echo", "PASS")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "PASS\n")

    def test_unknown_option_fails_closed(self):
        result = self.invoke("-unknown", "/bin/true")
        self.assertEqual(result.returncode, 2)
        self.assertIn("P26_BLOCKED_FAKEROOT_WRAPPER_UNKNOWN_OPTION", result.stderr)

    def test_missing_command_fails_closed(self):
        result = self.invoke("-i", "input.state")
        self.assertEqual(result.returncode, 2)
        self.assertIn("P26_BLOCKED_FAKEROOT_WRAPPER_NO_COMMAND", result.stderr)

    def test_outside_fakeroot_delegates_to_original(self):
        result = self.invoke("--", "/bin/echo", "PASS", nested=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ORIGINAL:-- /bin/echo PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
