#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression: partition acceptance must not disappear under python -O."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/build/verify_p26_partition.py"


class OptimizedReadbackTests(unittest.TestCase):
    def test_invalid_partition_rejected_with_optimized_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "invalid.p26"
            receipt = Path(tmp) / "receipt.json"
            image.write_bytes(b"hsqs")
            receipt.write_text('{"signed": false}')
            result = subprocess.run(
                [sys.executable, "-O", str(SCRIPT),
                 "--image", str(image), "--receipt", str(receipt)],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("incorrect p26 size", result.stderr)
            self.assertNotIn("P26_INDEPENDENT_BYTE_LAYOUT_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
