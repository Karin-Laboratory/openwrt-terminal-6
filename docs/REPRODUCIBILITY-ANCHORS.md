# Build lineage anchors (2026-10-22)

The privately retained Test24 Ethernet report identifies the running Linux 6.18.44 test system as Test21-derived, with OpenWrt procd on slot A and SquashFS p26. Its verified kernel `arch/arm64/boot/Image` SHA-256 was:

`452c990144d6f935da6cfcab065223c741adf705093d30b9189704f60b54ca9c`

Test25 compile-gate workflow, located on private branch `research/mt6990-test25-persistent-ethernet-build`, references a self-hosted kernel source under an internal path, that Image hash, and `Module.symvers` SHA-256:

`b547302b40596731c23a6f811a1171a5731580db8098bd5edc1080c370116b96`

The Test24 live diagnostic module was built using that ABI and achieved Ethernet connectivity only after volatile SerDes/PCS/PLL initialization. The Test25 source file is staged PHY candidate code; the inspected Test25 README explicitly says it was not integrated or field-tested at the time of writing. Do not equate Test24 live success with Test25 cold-boot source integration.

**Blocking reproducibility gap:** These hashes identify artifacts, but do not uniquely identify the complete source commit, all applied kernel patches, OpenWrt feeds, firmware dependency set or legal-to-redistribute signing inputs. Public builds are therefore not yet claimed to reproduce the working image.

Next source manifest must record: canonical upstream URL and commit, public patch URLs and digests, board DTS provenance, feeds lock, OpenWrt config, kernel config, kernel image hash, rootfs manifest and independently verified build logs. Do not publish the original private paths, keys, extracted firmware or unit EEPROM.
