#!/usr/bin/env python3
"""Check GitHub Actions workflow shapes and bash syntax for shell run steps."""
from pathlib import Path
import subprocess
import sys

import yaml


class WorkflowError(Exception):
    pass


def check(path: Path) -> None:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
        raise WorkflowError("missing jobs mapping")
    for job_name, job in data["jobs"].items():
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            raise WorkflowError(f"{job_name}: missing steps list")
        names = set()
        for idx, step in enumerate(job["steps"]):
            if not isinstance(step, dict):
                raise WorkflowError(f"{job_name}: step {idx} is not a mapping")
            name = step.get("name", step.get("uses", str(idx)))
            if name in names:
                raise WorkflowError(f"{job_name}: duplicate step name: {name}")
            names.add(name)
            script = step.get("run")
            if script is None:
                continue
            if not isinstance(script, str):
                raise WorkflowError(f"{job_name}/{name}: run must be a string")
            shell = str(step.get("shell", job.get("defaults", {}).get("run", {}).get("shell", "bash")))
            if shell.startswith("bash") or shell == "sh":
                result = subprocess.run(["bash", "-n"], input=script, text=True,
                                        capture_output=True, check=False)
                if result.returncode:
                    raise WorkflowError(f"{job_name}/{name}: bash -n failed: {result.stderr.strip()}")


def main() -> int:
    paths = sorted(Path(".github/workflows").glob("*.yml"))
    if not paths:
        print("FAIL: no workflows found", file=sys.stderr)
        return 1
    failed = False
    for path in paths:
        try:
            check(path)
            print(f"PASS: {path}")
        except (yaml.YAMLError, WorkflowError) as exc:
            print(f"FAIL: {path}: {exc}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
