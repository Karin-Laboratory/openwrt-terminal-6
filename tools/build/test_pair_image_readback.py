#!/usr/bin/env python3
"""Offline byte-readback regression tests; no firmware assets required."""
import hashlib
import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest import mock

MODULE = pathlib.Path(__file__).with_name("compare_pair_repro_receipts.py")
spec = importlib.util.spec_from_file_location("pair_receipts", MODULE)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)


class ImageReadbackTests(unittest.TestCase):
    def test_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            payload = b"unsigned synthetic image" * 1024
            path.write_bytes(payload)
            self.assertEqual(
                pair.verify_image(str(path), hashlib.sha256(payload).hexdigest(), len(payload)),
                hashlib.sha256(payload).hexdigest(),
            )

    def test_identity_from_verified_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            alias = pathlib.Path(directory) / "alias"
            payload = b"distinct image identity"
            path.write_bytes(payload)
            alias.hardlink_to(path)
            expected = hashlib.sha256(payload).hexdigest()
            first = pair.verify_image(str(path), expected, len(payload), return_identity=True)
            second = pair.verify_image(str(alias), expected, len(payload), return_identity=True)
            self.assertEqual(first, second)
            self.assertEqual(first[0], expected)

    def test_cli_rejects_reused_image_inode(self):
        import contextlib
        import io
        import sys
        receipt = {field: "a" * 64 for field in pair.FIELDS}
        images = ["p25-a", "p25-b", "p26-a", "p26-b"]
        args = ["compare", "receipt-a", "receipt-b",
                "--p25-a", images[0], "--p25-b", images[1],
                "--p26-a", images[2], "--p26-b", images[3]]
        identities = iter([(0, 1), (0, 1)])
        with (
            mock.patch.object(sys, "argv", args),
            mock.patch.object(pair, "load_with_identity", side_effect=[
                (receipt, (1, 1)), (receipt, (1, 2))
            ]),
            mock.patch.object(
                pair, "verify_image",
                side_effect=lambda *a, **k: ("a" * 64, next(identities)),
            ),
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            with self.assertRaises(SystemExit) as caught:
                pair.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("four distinct files", stderr.getvalue())

    def test_cli_accepts_four_distinct_images_and_matching_receipts(self):
        import contextlib
        import io
        import sys
        receipt = {field: "a" * 64 for field in pair.FIELDS}
        args = ["compare", "receipt-a", "receipt-b",
                "--p25-a", "p25-a", "--p25-b", "p25-b",
                "--p26-a", "p26-a", "--p26-b", "p26-b"]
        identities = iter([(1, 1), (1, 2), (1, 3), (1, 4)])
        with (
            mock.patch.object(sys, "argv", args),
            mock.patch.object(pair, "load_with_identity", side_effect=[
                (receipt, (2, 1)), (receipt.copy(), (2, 2))
            ]),
            mock.patch.object(
                pair, "verify_image",
                side_effect=lambda *a, **k: ("a" * 64, next(identities)),
            ) as verifier,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(pair.main(), 0)
        self.assertEqual(verifier.call_count, 4)
        self.assertIn("REPRO_IMAGE_FULL_READBACK_PASS", output.getvalue())
        self.assertIn("REPRO_RECEIPT_HASHES_MATCH", output.getvalue())

    def test_cli_reports_mismatch_after_four_distinct_image_readbacks(self):
        import contextlib
        import io
        import sys
        receipt_a = {field: "a" * 64 for field in pair.FIELDS}
        receipt_b = receipt_a.copy()
        receipt_b["kernel_image_sha256"] = "b" * 64
        args = ["compare", "receipt-a", "receipt-b",
                "--p25-a", "p25-a", "--p25-b", "p25-b",
                "--p26-a", "p26-a", "--p26-b", "p26-b"]
        identities = iter([(1, 1), (1, 2), (1, 3), (1, 4)])
        with (
            mock.patch.object(sys, "argv", args),
            mock.patch.object(pair, "load_with_identity", side_effect=[
                (receipt_a, (2, 1)), (receipt_b, (2, 2))
            ]),
            mock.patch.object(
                pair, "verify_image",
                side_effect=lambda *a, **k: ("a" * 64, next(identities)),
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(pair.main(), 1)
        self.assertIn("REPRO_KERNEL_IMAGE_SHA256=DIFF", output.getvalue())
        self.assertIn("REPRO_RECEIPT_MISMATCH: kernel_image_sha256", output.getvalue())

    def test_cli_rejects_reused_receipt_inode_before_image_reads(self):
        import contextlib
        import io
        import sys
        receipt = {field: "a" * 64 for field in pair.FIELDS}
        args = ["compare", "receipt-a", "receipt-b",
                "--p25-a", "p25-a", "--p25-b", "p25-b",
                "--p26-a", "p26-a", "--p26-b", "p26-b"]
        with (
            mock.patch.object(sys, "argv", args),
            mock.patch.object(pair, "load_with_identity", side_effect=[
                (receipt, (2, 1)), (receipt.copy(), (2, 1))
            ]),
            mock.patch.object(pair, "verify_image") as verifier,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            with self.assertRaises(SystemExit) as caught:
                pair.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("different receipt files", stderr.getvalue())
        verifier.assert_not_called()

    def test_cli_rejects_incomplete_image_argument_set(self):
        import contextlib
        import io
        import sys
        with (
            mock.patch.object(sys, "argv", ["compare", "receipt-a", "receipt-b",
                                            "--p25-a", "p25-a"]),
            mock.patch.object(pair, "load_with_identity") as loader,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            with self.assertRaises(SystemExit) as caught:
                pair.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("all four image paths", stderr.getvalue())
        loader.assert_not_called()

    def test_require_images_rejects_receipt_only_invocation(self):
        import contextlib
        import io
        import sys
        with (
            mock.patch.object(sys, "argv", ["compare", "receipt-a", "receipt-b", "--require-images"]),
            mock.patch.object(pair, "load_with_identity") as loader,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            with self.assertRaises(SystemExit) as caught:
                pair.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("--require-images requires all four image paths", stderr.getvalue())
        loader.assert_not_called()

    def test_require_images_accepts_four_distinct_verified_images(self):
        import contextlib
        import io
        import sys
        receipt = {field: "a" * 64 for field in pair.FIELDS}
        args = ["compare", "receipt-a", "receipt-b", "--require-images",
                "--p25-a", "p25-a", "--p25-b", "p25-b",
                "--p26-a", "p26-a", "--p26-b", "p26-b"]
        identities = iter([(1, 1), (1, 2), (1, 3), (1, 4)])
        with (
            mock.patch.object(sys, "argv", args),
            mock.patch.object(pair, "load_with_identity", side_effect=[
                (receipt, (2, 1)), (receipt.copy(), (2, 2))
            ]),
            mock.patch.object(pair, "verify_image",
                              side_effect=lambda *a, **k: ("a" * 64, next(identities))) as verifier,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(pair.main(), 0)
        self.assertEqual(verifier.call_count, 4)
        self.assertIn("REPRO_IMAGE_FULL_READBACK_PASS", output.getvalue())

    def test_readback_is_bounded_to_expected_size(self):
        # Even a file that grows while being read must not cause an
        # unbounded stream of full-size reads.
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            payload = b"x" * (2 * 1024 * 1024)
            path.write_bytes(payload)
            original_fdopen = os.fdopen
            requests = []

            class TrackedStream:
                def __init__(self, wrapped):
                    self.wrapped = wrapped

                def __enter__(self):
                    self.wrapped.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.wrapped.__exit__(*args)

                def fileno(self):
                    return self.wrapped.fileno()

                def read(self, size=-1):
                    requests.append(size)
                    return self.wrapped.read(size)

            def tracking_fdopen(fd, mode):
                return TrackedStream(original_fdopen(fd, mode))

            with mock.patch.object(pair.os, "fdopen", side_effect=tracking_fdopen):
                self.assertEqual(
                    pair.verify_image(str(path), hashlib.sha256(payload).hexdigest(), len(payload)),
                    hashlib.sha256(payload).hexdigest(),
                )
            self.assertEqual(requests, [1024 * 1024, 1024 * 1024, 1])

    def test_append_during_read_is_rejected(self):
        # Simulate an image growing after the initial fstat but before EOF.
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            payload = b"x" * (1024 * 1024)
            path.write_bytes(payload)
            original_fdopen = os.fdopen

            class AppendingStream:
                def __init__(self, wrapped):
                    self.wrapped = wrapped
                    self.appended = False

                def __enter__(self):
                    self.wrapped.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.wrapped.__exit__(*args)

                def fileno(self):
                    return self.wrapped.fileno()

                def read(self, size=-1):
                    chunk = self.wrapped.read(size)
                    if not self.appended and size == len(payload):
                        self.appended = True
                        with path.open("ab") as writer:
                            writer.write(b"unexpected trailing byte")
                    return chunk

            with mock.patch.object(
                pair.os, "fdopen",
                side_effect=lambda fd, mode: AppendingStream(original_fdopen(fd, mode)),
            ):
                with self.assertRaisesRegex(ValueError, "grew beyond expected size"):
                    pair.verify_image(
                        str(path), hashlib.sha256(payload).hexdigest(), len(payload)
                    )

    def test_corruption_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            path.write_bytes(b"abcd")
            digest = hashlib.sha256(b"abcd").hexdigest()
            with self.assertRaises(ValueError):
                pair.verify_image(str(path), digest, 5)
            with self.assertRaises(ValueError):
                pair.verify_image(str(path), hashlib.sha256(b"abce").hexdigest(), 4)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "image"
            link = pathlib.Path(directory) / "link"
            path.write_bytes(b"data")
            link.symlink_to(path)
            with self.assertRaises(OSError):
                pair.verify_image(str(link), hashlib.sha256(b"data").hexdigest(), 4)


if __name__ == "__main__":
    unittest.main()
