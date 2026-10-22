# Runtime SGMII FDT inventory (non-invasive)

The Test25 live notes explicitly observed:
- `/sgmiisys@11305000`: original vendor-compatible string and `syscon`; no `phys` or `phy-names` at observation time.
- `/sgmiiphy@11E60000`: original vendor-compatible string and `syscon`; the PHY driver was not bound and no direct `power-domains` observed.
- Ethernet `mediatek,sgmiisys` references two phandle entries, reported as `0x6d, 0x6e`. Their provider mapping must be confirmed from the **same extracted FDT**, not inferred from the numeric value or another hardware model.
- Ethernet's selected clock provider reference was `0x24`, with clock IDs `0x2e..0x33`. The clock provider's identity and argument-cell count still require an exact-tree review.
- SGMII_TOP0/1 were on in one runtime observation. That does not prove correct PHY domain binding.

**Next concrete check, off-device:** If the device owner lawfully obtains a decompiled FDT, run:

```sh
python3 tools/inventory_sgmii_fdt.py /path/to/runtime.dts > /tmp/sgmii-inventory.json
```

This reads two named nodes only and prints the properties used for dependency analysis. It does not modify the FDT. The original full DTS, raw DTB, factory images, hardware secrets and EEPROM are not included in this repository. The tool makes no false claim to resolve numeric phandles on its own.

**Release blocker:** The source code of the full independent board DTS still requires verified power-domain provider definition and ID, shared PLL provider, MMIO ownership, matching Linux binding, and successful actual-kernel `dtbs_check`. Do not enable PHY/PCS hardware based solely on this inventory.
