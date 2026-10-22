#!/usr/bin/env python3
"""Non-destructive comparison of compatible strings from text Device Trees.

Input must be a text DTS/DTSI file provided by the operator, not a proprietary
device image. This heuristic does not validate hardware or image compatibility.
"""
import argparse
import json
import pathlib
import re

PATTERN = re.compile(r'\bcompatible\s*=\s*([^;]+);', re.MULTILINE)
STRINGS = re.compile(r'"([^"]+)"')

def parse(path):
    value = pathlib.Path(path).read_text(encoding="utf-8")
    return sorted({item for section in PATTERN.findall(value)
                   for item in STRINGS.findall(section)})

def compare(left, right):
    a, b = set(left), set(right)
    return {
        "shared": sorted(a & b),
        "target_only": sorted(a - b),
        "reference_only": sorted(b - a),
        "warning": "Overlapping compatible strings do not prove board compatibility."
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=pathlib.Path)
    parser.add_argument("reference", type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(compare(parse(args.target), parse(args.reference)),
                     indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
