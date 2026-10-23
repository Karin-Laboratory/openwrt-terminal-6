# Compile-only Device Tree experiment

`sbat6d-incomplete.dts` includes `mt6990-identity-only.dtsi`. The include
contains only the observed SoC compatible; it intentionally has no memory,
CPUs, interrupt controller, clocks, resets, power domains, storage or enabled
peripherals. The pair compiles into a DTB with both standalone `dtc` and the
Linux 6.18.55 Kbuild DTB target. It remains a non-bootable syntax checkpoint,
not a formal or installable board DTS.

The Linux 6.18.55 MediaTek root binding has no `mediatek,mt6990` root
compatible entry, and no verified board-specific compatible is available in
this repository. The Kbuild schema-check path was attempted with
`CHECK_DTBS=y DT_SCHEMA_FILES=mediatek.yaml`; it stopped before validating the
DTB because `dt-doc-validate` from the `dtschema` package is not installed in
the local environment. Therefore `dtbs_check` is **not run / not passed**. A
passing schema result cannot be claimed; do not add a guessed compatible or
weaken the upstream binding to make the scaffold appear valid.

The file `mt6990-air-terminal-6-sgmii1-experimental.dtso` is a **disabled Device Tree overlay source**, not a flashable or deployable board DTS. The two exact runtime node paths were noted in the Test25 plan following live FDT inspection. This work does **not** copy or redistribute a full OEM device tree.

The candidate deliberately only marks compatible identifiers and `#phy-cells = <0>` while keeping both nodes **disabled**. It DOES NOT wire `phys`, power domains, clocks, resets, MMIO ranges, interrupt lines, MAC/DSA interfaces or signing details: those are pending evidence. Never change `status` to okay or apply this overlay without verifying the target running DT and complete dependencies.

Syntax-only check on an isolated host with dtc:

```sh
bash scripts/check-dtso.sh
```

Limitations: `dtc -@` can compile an overlay, but this does not prove a valid target path on arbitrary device revisions, correct overlay application, `dtbs_check`, driver binding, rootfs success, kernel safety or network operation. Overlay target paths are case-sensitive; the source currently records the developer-observed `/sgmiiphy@11E60000` and `/sgmiisys@11305000` strings pending an independent FDT recheck.

**Next**: review current FDT and phandle dependencies off-device, build an independently authored full board DTS, verify bindings, review SDK-related PHY/PCS rights, compile kernel with no signed output, then perform separately approved live tests.

## Offline dependency inspection

Use [`tools/audit_sgmii_dts.py`](../tools/audit_sgmii_dts.py) to inventory relevant properties from a locally acquired and permitted DTS. See [SGMII1 dependencies](SGMII1-DEPENDENCIES.md). The result is a preliminary, lexical check only and does not validate binding semantics or phandles.
