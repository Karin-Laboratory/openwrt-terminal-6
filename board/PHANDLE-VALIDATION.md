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
