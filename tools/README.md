# Safe, source-only development tools

## DTS compatible string comparison

Run with two operator-provided **text** DTS files:

```sh
python3 tools/dts_compat_audit.py target.dts reference.dts
python3 -m unittest discover -s tests -p 'test_*.py'
```

The resulting JSON lists common and differing `compatible` properties.
It never reads a partition or flashes hardware. Do **not** upload restricted
manufacturer DTS extractions or device-specific secrets to this repository.

Identical compatible strings cannot demonstrate wiring, MMIO, clocks, PHY,
partition layout, signatures or safe compatibility.

This helper is original public-project implementation based on the general
comparison requirement and does not copy archived vendor binary material.
