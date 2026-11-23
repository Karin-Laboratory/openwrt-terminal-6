#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual final P25/P26 receipt gate without a kernel rebuild."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/manufacture-public-openwrt-p25-from-debian14.sh"
START = 'python3 - "$p25" "$p26" "$out/unsigned-pair/same-run-p25-p26-receipt.json" <<\'PY\'\n'
END = '\nPY\n# Read the complete images again'


def final_gate():
    source = SCRIPT.read_text(encoding="utf-8")
    if source.count(START) != 1 or source.count(END) != 1:
        raise AssertionError("final gate extraction anchor changed")
    return source.split(START, 1)[1].split(END, 1)[0]


class FinalReceiptGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.p25 = self.base / "p25"
        self.p26 = self.base / "p26"
        self.receipt = self.base / "receipt.json"
        self.p25.write_bytes(b"synthetic-p25")
        self.p26.write_bytes(b"synthetic-p26")
        self.data = {
            "status": "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED",
            "p25_sha256": hashlib.sha256(self.p25.read_bytes()).hexdigest(),
            "p26_sha256": hashlib.sha256(self.p26.read_bytes()).hexdigest(),
        }
        self.save()

    def save(self):
        self.receipt.write_text(json.dumps(self.data), encoding="utf-8")

    def run_gate(self):
        return subprocess.run(
            ["python3", "-", str(self.p25), str(self.p26), str(self.receipt)],
            input=final_gate(), text=True, capture_output=True, check=False,
        )

    def test_matching_receipt(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PUBLIC_PAIR_FINAL_RECEIPT_READBACK_PASS", result.stdout)

    def test_swapped_receipt_digests(self):
        self.data["p25_sha256"], self.data["p26_sha256"] = (self.data["p26_sha256"], self.data["p25_sha256"])
        self.save()
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PUBLIC_PAIR_BLOCKED_FINAL_IMAGE_RECEIPT_MISMATCH_p25_sha256", result.stderr)

    def test_p25_mutated_after_receipt(self):
        self.p25.write_bytes(b"changed")
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_p26_mutated_after_receipt(self):
        self.p26.write_bytes(b"changed")
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_duplicate_json_key(self):
        self.receipt.write_text(self.receipt.read_text()[:-1] + ',"status":"UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED"}')
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_nonfinite_constant(self):
        self.receipt.write_text(self.receipt.read_text()[:-1] + ',"extra":NaN}')
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_invalid_digest(self):
        self.data["p25_sha256"] = "A" * 64
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_receipt_symlink(self):
        target = self.base / "target.json"
        self.receipt.rename(target)
        self.receipt.symlink_to(target)
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_replaced_p25_path_rejected(self):
        # Simulate replacement during the final digest without racing timing:
        # monkeypatch the stream read to atomically replace the pathname.
        gate = final_gate()
        injection = """
import builtins
_original_open = os.open
_original_fdopen = os.fdopen
_replaced = False
def _swap_fdopen(fd, *args, **kwargs):
    global _replaced
    if not _replaced:
        _replaced = True
        replacement = p25.with_name("replacement-p25")
        replacement.write_bytes(p25.read_bytes())
        os.replace(replacement, p25)
    return _original_fdopen(fd, *args, **kwargs)
os.fdopen = _swap_fdopen
"""
        # Insert just before the image digest loop, after receipt validation.
        anchor = 'for path, field in ((p25, "p25_sha256"), (p26, "p26_sha256")):'
        self.assertIn(anchor, gate)
        gate = gate.replace(anchor, injection + "\n" + anchor, 1)
        result = subprocess.run(
            ["python3", "-", str(self.p25), str(self.p26), str(self.receipt)],
            input=gate, text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PUBLIC_PAIR_BLOCKED_FINAL_IMAGE_REPLACED_p25_sha256", result.stderr)

    def test_image_symlink(self):
        target = self.base / "target.bin"
        self.p25.rename(target)
        self.p25.symlink_to(target)
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_wrong_status_value(self):
        self.data["status"] = "PENDING"
        self.save()
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PUBLIC_PAIR_FINAL_RECEIPT_READBACK_PASS", result.stdout)

    def test_p26_directory(self):
        self.p26.unlink()
        self.p26.mkdir()
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PUBLIC_PAIR_FINAL_RECEIPT_READBACK_PASS", result.stdout)

    def test_p25_digest_valid_format_wrong_bytes(self):
        self.data["p25_sha256"] = "0" * 64
        self.save()
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PUBLIC_PAIR_BLOCKED_FINAL_IMAGE_RECEIPT_MISMATCH_p25_sha256", result.stderr)
        self.assertNotIn("PUBLIC_PAIR_FINAL_RECEIPT_READBACK_PASS", result.stdout)

    def test_missing_status(self):
        del self.data["status"]
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_wrong_status_type(self):
        self.data["status"] = ["UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED"]
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_receipt_array(self):
        self.receipt.write_text("[]", encoding="utf-8")
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_receipt_invalid_utf8(self):
        self.receipt.write_bytes(bytes([0xff]))
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_missing_p26_digest(self):
        del self.data["p26_sha256"]
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_p26_symlink(self):
        target = self.base / "p26-target.bin"
        self.p26.rename(target)
        self.p26.symlink_to(target)
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_missing_p25_image(self):
        self.p25.unlink()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_receipt_oversize(self):
        self.receipt.write_bytes(b" " * (1024 * 1024 + 1))
        self.assertNotEqual(self.run_gate().returncode, 0)


    def test_missing_receipt(self):
        self.receipt.unlink()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_truncated_receipt_json(self):
        self.receipt.write_text('{"status":', encoding="utf-8")
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_missing_p25_digest(self):
        del self.data["p25_sha256"]
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_p26_digest_uppercase(self):
        self.data["p26_sha256"] = self.data["p26_sha256"].upper()
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)


    def test_p25_digest_wrong_type(self):
        self.data["p25_sha256"] = ["0" * 64]
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_p26_digest_null(self):
        self.data["p26_sha256"] = None
        self.save()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_receipt_directory(self):
        self.receipt.unlink()
        self.receipt.mkdir()
        self.assertNotEqual(self.run_gate().returncode, 0)

    def test_p25_directory(self):
        self.p25.unlink()
        self.p25.mkdir()
        self.assertNotEqual(self.run_gate().returncode, 0)

if __name__ == "__main__":
    unittest.main()
