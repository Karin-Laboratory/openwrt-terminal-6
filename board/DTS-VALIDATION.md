# Compile-only Device Tree experiment

`sbat6d-incomplete.dts` is an independently authored, **non-bootable research
scaffold**. It records only the observed SoC compatible and board model string.
It intentionally has no memory, CPUs, interrupt controller, clocks, resets,
power domains, storage or enabled peripherals. It compiles with `dtc` as a
syntax checkpoint, but is not a formal or installable board DTS and must not be
used to boot a device.

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
