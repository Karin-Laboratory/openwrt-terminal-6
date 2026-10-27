# Rights-aware OpenWrt MT6990 donor source acquisition

This step assists **source inspection only**, NOT a runnable SBAT6 target, rootfs reproduction, signing or flashing guide.

## Pinned public donor

- Repository: [13179415360/openwrt-mt6990-lg6851f](https://github.com/13179415360/openwrt-mt6990-lg6851f)
- Exact commit: `a40df9a5afb46716dea799acea69f17480df4d82`
- Reviewed source files and Git blobs: `target/linux/mediatek/Makefile` = `77b27878987e53e83be3d40dc342753e3734ac75`, `mt6990/target.mk` = `c98113e8a8cc9ee334eef28428972d8e9d4404e7`, `image/mt6990.mk` = `714551500ccd45bd3dfc77f951f104e0c46a660b`.
- Source-only fetch script: `bash scripts/fetch-pinned-openwrt-donor.sh /path/to/new-local-directory`. It refuses root, refuses existing destinations and validates the checkout revision. The source is downloaded directly by each authorized researcher, not mirrored here.

## Critical donor-vs-device distinction

The donor target's `Device/fiberhome_lg6851f` explicitly calls an LG6851F-specific Android boot packer and creates `boot_b.img` and `rootfs_b.img`. The donor also assumes LG6851F-specific DTS, an F2FS loop overlay and a package set including `luci-app-5gmodem` and radio-related modules. These choices **cannot** be treated as the SoftBank Air Terminal 6 partition layout, safe default userspace configuration, signing chain or redistributable runtime.

**Do not run the donor's device image build as an SBAT6 installable target.** The current repo intentionally does not vendor-copy its target image recipes or binary packages.

## Needed to move to a clean SBAT6 source-only OpenWrt rootfs build

1. Establish separately owned and rights-cleared MT6990 SoC kernel/driver sources and a correct SBAT6 board DTS. The disabled SGMII1 overlay is merely topology evidence.
2. Pin OpenWrt source, all feeds, download digests, toolchain and package inputs. The one donor commit does not pin feeds or package license status.
3. Create a **distinct** SBAT6 profile with noninstallable package/rootfs build goals and no vendor boot packer, signing or partition-write image definition.
4. Audit radio firmware, MT7990 device-specific EEPROM, modemd/RIL/CCCI dependencies, OpenWrt package distribution rights and first-boot default credentials.
5. Verify ABI, reproducible rootfs, cold-boot Ethernet/Wi-Fi/modem integration and independent recovery **before** any flashable artifact or upstream claim.

Original firmware images, signed partitions, private keys, device calibration and OEM provisioning remain in permanent Private archives.

## Current verdict

**Source acquisition: available; official independent OpenWrt target and clean build: NOT IMPLEMENTED.** A donor source checkout is not evidence that SBAT6 boots or that the cellular network operates in NR mode.
