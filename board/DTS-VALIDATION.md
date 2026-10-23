# Compile-only Device Tree experiment

`sbat6d-incomplete.dts` includes `mt6990.dtsi`. It records four Cortex-A55
CPU nodes, PSCI, GICv3 and the architected timer from the read-only B-unit
boot_b FDT. The ambiguous memory map and peripherals with unresolved MT6990
provider dependencies are omitted. This is a non-bootable partial tree.

`board/patches/0001-arm-dt-mediatek-add-mt6990-root-compatible.patch` adds the
two root compatible strings observed in the B-unit FDT. Linux 6.18.55 Kbuild
generated the DTB, `dt_binding_check` and `dt-doc-validate` passed for the
modified MediaTek root binding, and the target DTB passed an isolated
`dt-validate` run against the processed schema. A full MediaTek `dtbs_check`
also traverses unrelated existing boards and reports pre-existing schema
errors; those are not attributed to this target. The SoC peripheral providers
and their bindings are still missing.

The file `mt6990-air-terminal-6-sgmii1-experimental.dtso` is a **disabled Device Tree overlay source**, not a flashable or deployable board DTS. The two exact runtime node paths were noted in the Test25 plan following live FDT inspection. This work does **not** copy or redistribute a full OEM device tree.

The candidate deliberately only marks compatible identifiers and `#phy-cells = <0>` while keeping both nodes **disabled**. It DOES NOT wire `phys`, power domains, clocks, resets, MMIO ranges, interrupt lines, MAC/DSA interfaces or signing details: those are pending evidence. Never change `status` to okay or apply this overlay without verifying the target running DT and complete dependencies.

Syntax-only check on an isolated host with dtc:

```sh
bash scripts/check-dtso.sh
```

Limitations: `dtc -@` can compile an overlay, but this does not prove a valid target path on arbitrary device revisions, correct overlay application, `dtbs_check`, driver binding, rootfs success, kernel safety or network operation. Overlay target paths are case-sensitive; the source currently records the developer-observed `/sgmiiphy@11E60000` and `/sgmiisys@11305000` strings pending an independent FDT recheck.

**Next**: resolve usable RAM/reserved-memory, implement licensed MT6990 clock,
reset, genpd and pinctrl support, then add dependent eMMC/PCIe/Ethernet nodes
and verify every new node through `dtbs_check`. Do not use this tree to boot.

## Offline dependency inspection

Use [`tools/audit_sgmii_dts.py`](../tools/audit_sgmii_dts.py) to inventory relevant properties from a locally acquired and permitted DTS. See [SGMII1 dependencies](SGMII1-DEPENDENCIES.md). The result is a preliminary, lexical check only and does not validate binding semantics or phandles.
