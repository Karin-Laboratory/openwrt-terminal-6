# SGMII1 dependency review

Developer Test25 evidence identifies **existing** target paths `/sgmiisys@11305000` and `/sgmiiphy@11E60000`. The original runtime FDT showed vendor `compatible` strings but lacked the new driver's `phys` / `phy-names` link and a demonstrated PHY power-domain attachment.

| Element | Observed | Proposed, unverified |
| --- | --- | --- |
| SGMIISYS1 | 0x11305000, vendor compatible, syscon | driver matching MT6990 compatible, `phys`, `phy-names` |
| Analog PHY1 | 0x11e60000, vendor compatible | MT6990 PHY driver match, `#phy-cells = <0>` |
| Shared PLL | test address 0x10014000 + 0x8 | authoritative syscon provider/phandle |
| Power domain | TOP0/1 on in runtime summary | TOP1 provider, domain ID and PM ownership |
| Ethernet | MAC1 / PCS1, two `mediatek,sgmiisys` handles | preserve index order, avoid duplicated NETSYS children |
| Switch | MT7531 CPU port 5 / user port 1 | permanent DSA wiring and safe boot ordering |

These values are **read-only observed evidence**, not a complete board DTS. No vendor DTS text, device-identifying calibration or PHY initialization binary is included.

Run a preliminary text inventory on a locally and lawfully obtained DTS with:
```sh
python3 tools/audit_sgmii_dts.py /path/to/your-decompiled-board.dts
```

The tool shows missing property names but **cannot** verify phandles, register overlap or the semantic validity of IDs. Use `dtc` and kernel `dtbs_check` with the correct, separately reviewed bindings before considering a functional DTS. The existing experimental overlay stays disabled.

## Source-level reference gate

`python3 tools/check_sgmii_phandles.py board.dts` checks for a named `phys = <&label>` link from SGMIISYS1 to the matching PHY1 node and required PHY property names. Tests cover missing/mismatched links and missing power dependencies. The gate deliberately **fails** on the current unconnected experimental overlay; it is for reviewing a future fully authored board DTS, not for validating the disabled overlay.

This lexical gate does not inspect the provider implementation, numeric power domain, clock or PLL correctness. `dtc`, `dtbs_check`, source ownership and actual hardware testing remain separately required.
