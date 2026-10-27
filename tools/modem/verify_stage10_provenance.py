# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""Read-only verification of retained source and binary provenance; no devices."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('stage10',ROOT/'scripts/research/sba6d_stage10_clean_patch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--stage10',type=Path,required=True);a=p.parse_args()
expected={'drivers/net/ethernet/mediatek/mtk_eth_soc.c':'091175f8fbffe3368798c94b580882a2d6991a078d3703fac79af70befe789c9',m.DP:m.DP_SHA,m.MED:m.MED_SHA,'.config':'70aedc51dbb773409230c67f776764bf4d4b5e4164b2372c8082d13f25fd63b7','arch/arm64/boot/Image':'f4ebd3c4b9dc77fb5c514b6bfbbadc4959fdd6b1b2b2ee99743a4d7aa6c82203'}
assert m.transform((a.parent/m.ETH).read_bytes())==(a.stage10/m.ETH).read_bytes(),'transform mismatch'
for rel,h in expected.items():assert hashlib.sha256((a.stage10/rel).read_bytes()).hexdigest()==h,rel
print(json.dumps({'status':'PASS','checks':len(expected)+1,'scope':'retained Stage10 source/Image; not a new device test'}))
