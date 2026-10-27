# Offline build-artifact integrity, not signing

The source-only verifier [tools/boot/verify_build_inputs.py](../tools/boot/verify_build_inputs.py) checks file identities of **locally and independently obtained** build inputs against a strict JSON manifest. It is a bookkeeping and corruption-detection tool, not a trusted boot or cryptographic signature verifier.

- Accepts a local `--root` and `--manifest`. It never downloads, signs, flashes, reboots, reads device partitions, invokes an OEM SDK or writes files.
- Requires an explicit 40-hex source revision, allowed input roles (kernel, rootfs, DTB, metadata), per-file SHA-256 and exact file size.
- Rejects path traversal, symlinks, unsupported roles, duplicated inputs, private key/certificate extensions and oversized artifacts.
- The official research image, signing keys, OEM blobs and calibration remain in separate permanent Private archives. No real firmware manifest is provided here.

A passing check shows only **byte integrity relative to the supplied JSON**. It does **not** establish who signed anything, whether an SDK license permits use, whether a signature is trusted by LK, whether the image boots or whether A/B rescue will work.

To distribute firmware, additional independent evidence remains mandatory: build provenance, authenticated release signing, signer rights, secure initial administration, real device compatibility and independently proven recovery. See [release gates](RELEASE-GATES.md).

All repository regression tests use synthetic textual fixtures and cannot access device boot slots, keys, or firmware partitions.
