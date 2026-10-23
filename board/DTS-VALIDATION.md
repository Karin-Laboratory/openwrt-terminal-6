# Compile-only Device Tree experiment

`sbat6d-incomplete.dts` includes `mt6990.dtsi` and
`mt6990-observed-peripherals.dtsi`. It records CPU/PSCI/GIC/timer plus a
sanitized inventory of observed UART0, eMMC, PCIe roots/PHYs, Ethernet MACs
and SGMII resources. All peripheral/provider nodes are `status = "disabled"`;
the conflicting RAM map is omitted. Firmware-specific SGMII relationship
properties without an upstream consumer binding are documented, not copied
into this tree. This is a non-bootable partial tree.

`board/patches/0001-arm-dt-mediatek-add-mt6990-root-compatible.patch` adds the
two root compatible strings observed in the B-unit FDT. Linux 6.18.55 Kbuild
generated `mt6990-sbat6d-incomplete.dtb` (SHA-256
`82c8d70a7a89dc66cf04df80b1a72eb946e8391a390c530de99c55d6412241be`). The
target DTB passed isolated `dt-validate` with no diagnostics. Targeted
`dt_binding_check` completed for the modified MediaTek root binding and the
standard MediaTek UART binding; dtschema reported an unrelated existing
Realtek schema warning and skipped yamllint because it is not installed. A
full MediaTek `CHECK_DTBS=y dtbs` walk exited zero but printed schema errors
for unrelated existing MT7988 boards; it is not a clean full-tree pass and
those errors did not name this target. Peripheral providers, subsystem
bindings and drivers remain incomplete.

The file `mt6990-air-terminal-6-sgmii1-experimental.dtso` remains a **disabled Device Tree overlay source**, not a flashable or deployable board DTS. This work does **not** copy or redistribute a full OEM device tree.

Never change an observed peripheral's `status` to `okay` or apply the overlay without implementing and verifying all required providers, drivers and board dependencies.

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
