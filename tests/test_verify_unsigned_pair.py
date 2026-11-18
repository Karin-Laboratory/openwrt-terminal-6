# SPDX-License-Identifier: MIT
"""Host-only rejection tests of unsigned pair receipt identity gates."""
import hashlib
import inspect
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "tools/build/verify_unsigned_pair.py"
spec = importlib.util.spec_from_file_location("verify_unsigned_pair", MODULE)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)


class PairTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.p25 = self.base / "p25"
        self.p26 = self.base / "p26"
        self.p25.write_bytes(b"boot-v2-test" + bytes(64 - len(b"boot-v2-test")))
        self.p26.write_bytes(b"hsqs-test" + bytes(128 - len(b"hsqs-test")))
        self.parts = [self.base / f for f in ("kernel", "ramdisk", "dtb", "cfg")]
        for part in self.parts[:3]:
            part.write_text("synthetic")
        self.parts[3].write_text(json.dumps({"ramdisk_mode": "kernel_embedded"}))
        self.producer = self.base / "producer.json"
        self.independent = self.base / "independent.json"
        self.out = self.base / "pair.json"
        self.cpio = self.base / "initramfs.cpio"
        self.initramfs_object = self.base / "initramfs_data.o"
        self.vmlinux = self.base / "vmlinux"
        self.image = self.base / "Image"
        for path in (self.initramfs_object, self.vmlinux, self.image):
            path.write_bytes(b"synthetic")
        self.cpio.write_bytes(b"newc" + pair.digest(self.p26).encode("ascii") +
                              b"  /dev/mmcblk0p26" + b"TRAILER!!!")
        self.producer.write_text(json.dumps({
            "schema": 1, "status": "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK",
            "signed": False, "hardware": "NONE",
            "partition_bytes": 128,
            "p26_sha256": pair.digest(self.p26),
            "squashfs_sha256": "f" * 64, "squashfs_bytes": 9
        }))
        self.update_independent()
        patches = [patch.object(pair, "P25_BYTES", 64),
                   patch.object(pair, "P26_BYTES", 128)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def update_independent(self):
        prod = json.loads(self.producer.read_text())
        self.independent.write_text(json.dumps({
            "schema": 1, "status": "P26_INDEPENDENT_FS_READBACK_VERIFIED",
            "signed": False, "hardware": "NONE", "partition_bytes": 128,
            "verification": "INDEPENDENT_FULL_PARTITION_AND_EXTRACTED_METADATA",
            "p26_sha256": prod["p26_sha256"],
            "producer_receipt_sha256": pair.digest(self.producer),
            "squashfs_sha256": prod["squashfs_sha256"],
            "squashfs_bytes": prod["squashfs_bytes"]
        }))

    def fake_p25(self, *args):
        return {"partition_bytes": 64, "header_version": 2,
                "scope": "UNSIGNED_V2_BYTE_LAYOUT_ONLY",
                "ramdisk_mode": "kernel_embedded",
                "p25_sha256": pair.digest(self.p25)}

    def fake_initramfs(self, *args):
        return {"status": "ARM64_KERNEL_INITRAMFS_OBJECT_AND_IMAGE_VERIFIED",
                "compression": "xz", "cpio_sha256": pair.digest(self.cpio),
                "kernel_image_sha256": pair.digest(self.image),
                "kernel_gzip_sha256": pair.digest(self.parts[0])}

    def run_pair(self):
        return pair.verify_pair(self.p25, *self.parts, self.p26,
                                self.producer, self.independent,
                                self.cpio, self.initramfs_object,
                                self.vmlinux, self.image, self.out,
                                p25_verify=self.fake_p25,
                                initramfs_verify=self.fake_initramfs)

    def test_cpio_changed_after_scan_rejected_before_receipt(self):
        original_digest = pair.digest
        calls = 0

        def mutate_after_scan(path):
            nonlocal calls
            result = original_digest(path)
            if path == self.p26:
                calls += 1
                # Second P26 digest occurs after the CPIO marker scan.
                if calls == 2:
                    with self.cpio.open("ab") as stream:
                        stream.write(b"late mutation")
            return result

        with patch.object(pair, "digest", side_effect=mutate_after_scan):
            with self.assertRaisesRegex(ValueError, "CPIO_CHANGED_BEFORE_RECEIPT"):
                self.run_pair()
        self.assertFalse(self.out.exists())

    def test_kernel_artifacts_changed_after_attestation_rejected(self):
        for target, reason in ((self.parts[0], "KERNEL_GZIP_CHANGED"),
                               (self.image, "KERNEL_IMAGE_CHANGED"),
                               (self.initramfs_object, "INITRAMFS_OBJECT_CHANGED")):
            with self.subTest(target=target.name):
                original = target.read_bytes()
                original_digest = pair.digest
                triggered = False

                def mutate_on_p26_final_digest(path):
                    nonlocal triggered
                    result = original_digest(path)
                    # The object baseline is captured while constructing the
                    # receipt, after the initial P26 hash. Mutate immediately
                    # after that baseline; other artifacts are already attested.
                    mutation_point = (self.initramfs_object
                                      if target == self.initramfs_object
                                      else self.p26)
                    if path == mutation_point and not triggered:
                        triggered = True
                        target.write_bytes(original + b"changed")
                    return result

                with patch.object(pair, "digest", side_effect=mutate_on_p26_final_digest):
                    with self.assertRaisesRegex(ValueError, reason):
                        self.run_pair()
                self.assertFalse(self.out.exists())
                target.write_bytes(original)

    def test_pair_identity_pass_and_refuse_overwrite(self):
        evidence = self.run_pair()
        self.assertEqual(evidence["status"], "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED")
        self.assertEqual(json.loads(self.out.read_text())["p26_sha256"],
                         pair.digest(self.p26))
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
            self.run_pair()

    def test_receipt_sync_failure_removes_partial_evidence(self):
        # The first fsync targets the receipt file; rollback must sync its
        # parent directory after unlinking the incomplete receipt.
        import os
        real_fsync = os.fsync
        calls = []

        def fail_first_fsync(fd):
            calls.append(fd)
            if len(calls) == 1:
                raise OSError("synthetic receipt sync failure")
            return real_fsync(fd)

        with patch.object(pair.os, "fsync", side_effect=fail_first_fsync):
            with self.assertRaisesRegex(OSError, "synthetic receipt sync failure"):
                self.run_pair()
        self.assertFalse(self.out.exists())
        self.assertGreaterEqual(len(calls), 2)

    def test_directory_sync_failure_removes_receipt(self):
        # File data may be durable while the directory entry is not.
        # The failed parent sync must roll back the newly created receipt.
        import os
        real_fsync = os.fsync
        calls = []

        def fail_directory_sync(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError("synthetic directory sync failure")
            return real_fsync(fd)

        with patch.object(pair.os, "fsync", side_effect=fail_directory_sync):
            with self.assertRaisesRegex(OSError, "synthetic directory sync failure"):
                self.run_pair()
        self.assertFalse(self.out.exists())
        self.assertGreaterEqual(len(calls), 3)

    def test_receipt_json_failure_removes_partial_evidence(self):
        with patch.object(pair.json, "dump", side_effect=OSError("synthetic short write")):
            with self.assertRaisesRegex(OSError, "synthetic short write"):
                self.run_pair()
        self.assertFalse(self.out.exists())

    def test_metadata_mutation_after_parse_rejected(self):
        for target, reason in ((self.parts[3], "P25_CONFIG_CHANGED"),
                               (self.producer, "P26_PRODUCER_RECEIPT_CHANGED"),
                               (self.independent, "P26_INDEPENDENT_RECEIPT_CHANGED")):
            with self.subTest(target=target.name):
                original = target.read_bytes()
                original_read = pair.read_receipt

                def mutate_after_read(path):
                    result = original_read(path)
                    if path == target:
                        path.write_bytes(original + b" ")
                    return result

                with patch.object(pair, "read_receipt", side_effect=mutate_after_read):
                    with self.assertRaisesRegex(ValueError, reason):
                        self.run_pair()
                self.assertFalse(self.out.exists())
                target.write_bytes(original)

    def test_initramfs_attestation_must_match_exact_inputs(self):
        valid = self.fake_initramfs()
        for field in ("cpio_sha256", "kernel_image_sha256",
                      "kernel_gzip_sha256", "status", "compression"):
            with self.subTest(field=field):
                invalid = dict(valid)
                invalid[field] = "0" * 64
                with self.assertRaisesRegex(ValueError, "INITRAMFS_ATTESTATION_IDENTITY"):
                    pair.verify_pair(self.p25, *self.parts, self.p26,
                                     self.producer, self.independent, self.cpio,
                                     self.initramfs_object, self.vmlinux,
                                     self.image, self.out,
                                     p25_verify=self.fake_p25,
                                     initramfs_verify=lambda *args: invalid)
                self.assertFalse(self.out.exists())

    def test_mismatched_initramfs_p26_hash_rejected(self):
        self.cpio.write_bytes(b"newc" + b"0" * 64 + b"  /dev/mmcblk0p26")
        with self.assertRaisesRegex(ValueError, "P26_INITRAMFS_SHA_BINDING"):
            self.run_pair()
        self.assertFalse(self.out.exists())

    def test_p26_binding_spans_stream_chunk_boundary(self):
        marker = pair.digest(self.p26).encode("ascii") + b"  /dev/mmcblk0p26"
        # The marker crosses the 1 MiB streaming read boundary.
        self.cpio.write_bytes(b"x" * (1024 * 1024 - 20) + marker)
        self.assertEqual(self.run_pair()["status"],
                         "UNSIGNED_PAIR_BYTE_IDENTITIES_VERIFIED")

    def test_duplicate_p26_binding_across_chunks_rejected(self):
        marker = pair.digest(self.p26).encode("ascii") + b"  /dev/mmcblk0p26"
        self.cpio.write_bytes(marker + b"x" * (1024 * 1024) + marker)
        with self.assertRaisesRegex(ValueError, "P26_INITRAMFS_SHA_BINDING"):
            self.run_pair()
        self.assertFalse(self.out.exists())

    def test_cpio_replaced_after_initial_attestation_is_rejected(self):
        # The initial digest agrees with the independent initramfs verifier.
        # Replacing the CPIO before the marker scan must not yield a receipt.
        original_digest = pair.digest
        cpio_reads = 0

        def replace_after_digest(path):
            nonlocal cpio_reads
            value = original_digest(path)
            if path == self.cpio:
                cpio_reads += 1
            if path == self.cpio and cpio_reads == 2:
                # Preserve the marker, but change bytes elsewhere.
                self.cpio.write_bytes(self.cpio.read_bytes() + b"changed")
            return value

        with patch.object(pair, "digest", side_effect=replace_after_digest):
            with self.assertRaisesRegex(ValueError, "CPIO_CHANGED_DURING_VERIFICATION"):
                self.run_pair()
        self.assertGreaterEqual(cpio_reads, 2)
        self.assertFalse(self.out.exists())

    def test_cpio_modified_while_streaming_is_rejected(self):
        marker = pair.digest(self.p26).encode("ascii") + b"  /dev/mmcblk0p26"
        self.cpio.write_bytes(marker + b"x" * (1024 * 1024 + 64))
        original_fdopen = os.fdopen
        original_open = Path.open
        target = self.cpio

        class MutatingStream:
            def __init__(self, stream):
                self.stream = stream
                self.reads = 0

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def read(self, size=-1):
                data = self.stream.read(size)
                self.reads += 1
                if self.reads == 1:
                    with original_open(target, "r+b") as writer:
                        writer.seek(1024 * 1024)
                        writer.write(b"changed")
                return data

        original_digest = pair.digest
        cpio_reads = 0

        def track_attestation(path):
            nonlocal cpio_reads
            result = original_digest(path)
            if path == target:
                cpio_reads += 1
            return result

        def mutate_scan_fdopen(fd, mode="r", *args, **kwargs):
            stream = original_fdopen(fd, mode, *args, **kwargs)
            if mode == "rb" and cpio_reads >= 2:
                return MutatingStream(stream)
            return stream

        with patch.object(pair, "digest", side_effect=track_attestation):
            with patch.object(pair.os, "fdopen", side_effect=mutate_scan_fdopen):
                with self.assertRaisesRegex(ValueError, "CPIO_CHANGED_DURING_VERIFICATION"):
                    self.run_pair()
        self.assertFalse(self.out.exists())

    def test_cpio_scan_rejects_short_read_even_with_stable_metadata(self):
        # Simulate a short read on the scan stream without changing the inode.
        # The attestation digest must still read the complete original bytes.
        original_fdopen = os.fdopen

        class ShortStream:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def read(self, size=-1):
                return b""

        def truncate_scan(fd, mode="r", *args, **kwargs):
            stream = original_fdopen(fd, mode, *args, **kwargs)
            callers = {frame.function for frame in inspect.stack()}
            if (mode == "rb" and os.fstat(fd).st_ino == self.cpio.stat().st_ino
                    and "verify_pair" in callers and "digest" not in callers):
                return ShortStream(stream)
            return stream

        with patch.object(pair.os, "fdopen", side_effect=truncate_scan):
            with self.assertRaisesRegex(ValueError, "CPIO_CHANGED_DURING_VERIFICATION"):
                self.run_pair()
        self.assertFalse(self.out.exists())

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_cpio_symlink_swap_before_scan_is_rejected(self):
        # The verifier attests the original file, then an attacker swaps its
        # pathname for a symlink to another file with the same marker.
        original = pair.digest
        target = self.cpio
        swapped = False

        def swap_after_attestation(path):
            nonlocal swapped
            result = original(path)
            if path == target and not swapped:
                swapped = True
                replacement = self.base / "replacement.cpio"
                replacement.write_bytes(target.read_bytes())
                target.unlink()
                target.symlink_to(replacement)
            return result

        with patch.object(pair, "digest", side_effect=swap_after_attestation):
            with self.assertRaises(OSError):
                self.run_pair()
        self.assertFalse(self.out.exists())

    def test_p25_replaced_after_verification_is_rejected(self):
        # The boot image must still match the independently verified bytes
        # when the final pair receipt is about to be written.
        original_digest = pair.digest
        target = self.p25
        reads = 0

        def swap_after_initial_checks(path):
            nonlocal reads
            result = original_digest(path)
            if path == target:
                reads += 1
                if reads == 2:
                    target.write_bytes(b"X" + target.read_bytes()[1:])
            return result

        with patch.object(pair, "digest", side_effect=swap_after_initial_checks):
            with self.assertRaisesRegex(ValueError, "P25_CHANGED_DURING_VERIFICATION"):
                self.run_pair()
        self.assertFalse(self.out.exists())

    def test_p26_replaced_after_initial_digest_is_rejected(self):
        # Preserve the CPIO binding while mutating P26 after the first
        # digest, so the final receipt must reject stale image identity.
        original_digest = pair.digest
        target = self.p26
        reads = 0

        def mutate_after_digest(path):
            nonlocal reads
            result = original_digest(path)
            if path == target:
                reads += 1
                if reads == 1:
                    with target.open("r+b") as stream:
                        stream.seek(-1, os.SEEK_END)
                        stream.write(b"X")
            return result

        with patch.object(pair, "digest", side_effect=mutate_after_digest):
            with self.assertRaisesRegex(ValueError, "P26_CHANGED_DURING_VERIFICATION"):
                self.run_pair()
        self.assertFalse(self.out.exists())

    def test_changed_p26_rejected(self):
        image = bytearray(self.p26.read_bytes())
        image[-1] = 1
        self.p26.write_bytes(image)
        with self.assertRaisesRegex(ValueError, "P26_IMAGE_IDENTITY"):
            self.run_pair()
        self.assertFalse(self.out.exists())

    def test_wrong_producer_receipt_rejected(self):
        doc = json.loads(self.producer.read_text())
        doc["p26_sha256"] = "0" * 64
        self.producer.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "P26_IMAGE_IDENTITY|P26_RECEIPT_IDENTITY"):
            self.run_pair()

    def test_false_independent_status_rejected(self):
        doc = json.loads(self.independent.read_text())
        doc["status"] = "P26_PACKED_AWAIT_INDEPENDENT_FS_READBACK"
        self.independent.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "P26_NOT_INDEPENDENTLY_VERIFIED"):
            self.run_pair()

    def test_non_object_receipts_fail_closed(self):
        cases = ((self.parts[3], "P25_CONFIG_NOT_OBJECT"),
                 (self.producer, "P26_PRODUCER_NOT_OBJECT"),
                 (self.independent, "P26_ATTESTATION_NOT_OBJECT"))
        for path, marker in cases:
            original = path.read_text()
            for value in ("[]", "null", "true", "42", '"string"'):
                with self.subTest(path=path.name, value=value):
                    path.write_text(value)
                    with self.assertRaisesRegex(ValueError, marker):
                        self.run_pair()
                    self.assertFalse(self.out.exists())
            path.write_text(original)

    def test_oversized_receipts_fail_closed(self):
        for path in (self.parts[3], self.producer, self.independent):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(b" " * (pair.MAX_RECEIPT_BYTES + 1))
                with self.assertRaisesRegex(ValueError, "RECEIPT_TOO_LARGE"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
                path.write_bytes(original)

    def test_nonfinite_receipt_constants_fail_closed(self):
        for path in (self.parts[3], self.producer, self.independent):
            original = path.read_bytes()
            for token in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(path=path.name, token=token):
                    path.write_text('{"nonfinite": ' + token + '}')
                    with self.assertRaisesRegex(ValueError, "NONFINITE_JSON_CONSTANT"):
                        self.run_pair()
                    self.assertFalse(self.out.exists())
            path.write_bytes(original)

    def test_duplicate_receipt_keys_fail_closed(self):
        for path in (self.parts[3], self.producer, self.independent):
            with self.subTest(path=path.name):
                original = path.read_text()
                duplicate = '"ramdisk_mode": "kernel_embedded",' if path == self.parts[3] else '"schema": 1,'
                path.write_text(original.replace("{", "{" + duplicate, 1))
                with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
                path.write_text(original)

    def test_boolean_integer_fields_fail_closed(self):
        for path, field, marker in (
            (self.producer, "schema", "P26_PRODUCER_STATUS"),
            (self.independent, "schema", "P26_NOT_INDEPENDENTLY_VERIFIED"),
            (self.producer, "partition_bytes", "P26_SIZE"),
            (self.independent, "partition_bytes", "P26_SIZE"),
        ):
            with self.subTest(path=path.name, field=field):
                original = path.read_text()
                data = json.loads(original)
                data[field] = True if field == "schema" else False
                path.write_text(json.dumps(data))
                if path == self.producer:
                    self.update_independent()
                with self.assertRaisesRegex(ValueError, marker):
                    self.run_pair()
                self.assertFalse(self.out.exists())
                path.write_text(original)
                self.update_independent()

    def test_squashfs_boolean_size_rejected(self):
        for value in (True, False, 0, 128):
            with self.subTest(value=value):
                original = json.loads(self.producer.read_text())
                original["squashfs_bytes"] = value
                self.producer.write_text(json.dumps(original))
                self.update_independent()
                with self.assertRaisesRegex(ValueError, "P26_SQUASHFS_IDENTITY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
                original["squashfs_bytes"] = 9
                self.producer.write_text(json.dumps(original))
                self.update_independent()

    def test_invalid_squashfs_size_types_fail_closed(self):
        original = self.producer.read_text()
        for value in (True, False, 0, -1, 128, 129, "9", 9.0):
            with self.subTest(value=value):
                data = json.loads(original)
                data["squashfs_bytes"] = value
                self.producer.write_text(json.dumps(data))
                self.update_independent()
                with self.assertRaisesRegex(ValueError, "P26_SQUASHFS_IDENTITY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
        self.producer.write_text(original)
        self.update_independent()

    def test_malformed_squashfs_digest_rejected(self):
        original = self.producer.read_text()
        for digest in ("", "f" * 63, "f" * 65, "g" * 64,
                       "F" * 64, 123, True, None):
            with self.subTest(digest=digest):
                data = json.loads(original)
                data["squashfs_sha256"] = digest
                self.producer.write_text(json.dumps(data))
                self.update_independent()
                with self.assertRaisesRegex(ValueError, "P26_SQUASHFS_IDENTITY"):
                    self.run_pair()
                self.assertFalse(self.out.exists())
        self.producer.write_text(original)
        self.update_independent()

    def test_malformed_p25_verifier_result_rejected(self):
        for result in (None, [], True, {}, {"partition_bytes": 64},
                       {**self.fake_p25(), "header_version": 1},
                       {**self.fake_p25(), "scope": "UNVERIFIED"},
                       {**self.fake_p25(), "ramdisk_mode": "external"},
                       {**self.fake_p25(), "partition_bytes": True}):
            with self.subTest(result=result):
                with self.assertRaisesRegex(ValueError, "P25_IDENTITY"):
                    pair.verify_pair(
                        self.p25, *self.parts, self.p26, self.producer,
                        self.independent, self.cpio, self.initramfs_object,
                        self.vmlinux, self.image, self.out,
                        p25_verify=lambda *args: result,
                        initramfs_verify=self.fake_initramfs)
                self.assertFalse(self.out.exists())

    def test_p25_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, "P25_IDENTITY"):
            pair.verify_pair(self.p25, *self.parts, self.p26, self.producer,
                             self.independent, self.cpio,
                             self.initramfs_object, self.vmlinux, self.image,
                             self.out,
                             p25_verify=lambda *args: {**self.fake_p25(),
                                                       "p25_sha256": "0" * 64},
                             initramfs_verify=self.fake_initramfs)


    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_receipt_reader_rejects_symlink(self):
        alias = self.base / "receipt-link.json"
        alias.symlink_to(self.producer)
        with self.assertRaises(OSError):
            pair.read_receipt(alias)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX FIFO")
    def test_receipt_reader_rejects_fifo_without_blocking(self):
        fifo = self.base / "receipt-fifo"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, "RECEIPT_NOT_REGULAR"):
            pair.read_receipt(fifo)

    def test_receipt_reader_rejects_changed_metadata_during_read(self):
        original = pair.os.fstat
        calls = 0

        def altered_stat(fd):
            nonlocal calls
            calls += 1
            info = original(fd)
            if calls == 2:
                class Changed:
                    st_dev = info.st_dev
                    st_ino = info.st_ino
                    st_size = info.st_size - 1
                    st_mtime_ns = info.st_mtime_ns
                    st_ctime_ns = info.st_ctime_ns
                return Changed()
            return info

        with patch.object(pair.os, "fstat", side_effect=altered_stat):
            with self.assertRaisesRegex(ValueError, "RECEIPT_CHANGED_DURING_READ"):
                pair.read_receipt(self.producer)


if __name__ == "__main__":
    unittest.main()
