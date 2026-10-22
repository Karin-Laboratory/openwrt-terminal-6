# Runtime FDT numeric phandle reverse lookup

Source-only diagnostic: `tools/resolve_fdt_phandles.py`.

The Test25 developer report recorded Ethernet `mediatek,sgmiisys` handles `0x6d` and `0x6e`, and a clock reference to `0x24`. Those integers are **not stable across FDT builds** and must be resolved against the **same** off-device FDT that supplied them.

Run on a lawfully obtained, *decompiled textual* FDT:

```sh
python3 tools/resolve_fdt_phandles.py /path/to/device.dts
```

The script searches `phandle` / `linux,phandle` declarations, reports one provider path and text line when uniquely found, and returns nonzero on missing or multiple declarations. It never changes a file, emits vendor source or contacts a device.

**Limitations:** Preliminary line-oriented scanner; it does not fully parse DTS syntax, nested node braces on the same line, provider `#clock-cells`, power-domain schema, actual `phys` references, MMIO overlap, or driver compatibility. Numeric handles alone cannot establish that an SPM or PLL reference is valid. Independently verify against `dtc` and kernel bindings before publishing a functioning DTS.

This project deliberately does not store any private FDT content.
