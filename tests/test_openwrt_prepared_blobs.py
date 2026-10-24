# SPDX-License-Identifier: MIT
import tempfile
import unittest
from pathlib import Path

from tools.check_openwrt_prepared_blobs import git_blob_id, inspect


class OpenWrtPreparedBlobTests(unittest.TestCase):
    def test_git_blob_id_uses_git_object_header(self):
        self.assertEqual(
            git_blob_id(b"hello\n"),
            "ce013625030ba8dba906f756967f9e9ca394464a",
        )

    def test_missing_prepared_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            result = inspect(Path(directory))
        self.assertFalse(result["eligible_for_rebased_rfc_series"])
        self.assertEqual(
            {entry["state"] for entry in result["files"].values()},
            {"missing"},
        )


if __name__ == "__main__":
    unittest.main()
