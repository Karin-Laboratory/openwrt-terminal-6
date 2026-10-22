# Synthetic overlay integration test

This test uses only a hand-written, minimal synthetic DTS fixture. It intentionally cannot represent the running manufacturer's complete FDT. It compiles the fixture and the disabled experimental overlay, uses `fdtoverlay` to merge them and checks via `fdtget` that both target nodes remain disabled.

Run `bash scripts/verify-overlay-offline.sh` with Debian/Ubuntu `device-tree-compiler` installed. This validates absolute target path resolution on this synthetic fixture and overlay encoding, **not** correctness of actual device paths, register ranges, or phandle wiring on SoftBank Air Terminal 6.

The original FDT's power, clock and PLL phandle provider mapping remains unverified. Until an independently checked, distributable Air Terminal 6 board DTS is written, do not publish this as a functional PHY/PCS port or enable these nodes.
