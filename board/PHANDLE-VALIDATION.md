# SGMII1 reference resolution: synthetic compile gate

The current experimental overlay has intentionally no valid hardware provider
references. To test the phandle mechanism **without** inventing real board
power-domain IDs, a distinct synthetic fixture has been added at
`tests/fixtures/sgmii-linked.dts`.

It includes artificial labelled PLL and power-domain provider nodes, disabled
SGMII1/PHY1 nodes, and a PHY consumer reference. These fictitious providers
are for compiler acceptance only and **must not be incorporated into the
Air Terminal 6 board DTS**.

Run:

```sh
bash scripts/check-sgmii-linked-fixture.sh
```

It performs the source reference check, compiles a synthetic DTB and verifies
that `phys` and `power-domains` cells are present while both hardware nodes
remain disabled. A successful result establishes only *synthetic phandle
resolution*. It does not establish the real SPM address, domain ID, shared PLL
provider, kernel binding validity or safe PHY enablement.

Real-board GO requirements: obtain a legally reviewable current FDT; compare
node paths and phandle provider definitions; verify `#power-domain-cells` and
clock/PM dependencies; compile the actual independently authored DTS through
the Linux kernel's DT build and `dtbs_check`; validate PHY/PCS code attribution;
then perform separate controlled hardware testing.

## Test25 SGMII1 provider/consumer wiring experiment (2026-10-22)

The public **disabled overlay** now adds an internally resolved PHY1 label,
`#phy-cells = <0>`, `mediatek,sgmii-id = <1>`, and a matching
`phys = <&sbat6_phy1>` with `phy-names = "sgmii"` on the SGMIISYS1 consumer.
The hardware node paths and original vendor-compatible strings are preserved
as fallback compatibles. This models the **PHY consumer link only**; it does
not assert a working PHY driver or power sequencing.

`scripts/verify-overlay-offline.sh` checks the overlay merge against a
**synthetic** FDT, both nodes remain disabled, and the compiled consumer
`phys` cell equals the compiled PHY provider's `phandle` cell. This is
stronger than a purely lexical inspection, but not an actual hardware test.

**Explicitly absent:** `mediatek,sgmii-pll`, `mediatek,spm`,
`power-domains`. Enabling this node before authentic provider mapping,
clock/genpd ownership, source compile and controlled hardware trials is unsafe.

The code and documentation have been committed; successful CI and `dtc`
execution are not yet confirmed for this revision.
