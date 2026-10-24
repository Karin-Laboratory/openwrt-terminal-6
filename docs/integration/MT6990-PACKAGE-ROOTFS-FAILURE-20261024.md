# MT6990 package/rootfs failure analysis — 2026-10-24

## Run reviewed

[Actions run 40043771239](https://github.com/Karin-Laboratory/openwrt-terminal-6/actions/runs/40043771239)

The toolchain, Kconfig preflight, ARM64 kernel build, MediaTek Ethernet
compile, DTB generation and targeted schema checks passed. The job failed in
the step named **Build package and rootfs staging** before invoking
`package/compile`.

The first substantive error was the workflow's own stack-canary ABI gate:

```text
Effective kernel stack-protector ABI:
CONFIG_STACKPROTECTOR=y
Global stack-protector mode selected without an exported __stack_chk_guard.
```

No `gpio-button-hotplug.ko` compile was reached in this run. Therefore the
run does not establish a failure in that package, its source, or rootfs
assembly. The prior global-canary fallback was inappropriate for the target's
intended ARM64 per-task canary ABI.

## Evidence and source correction

The workflow's earlier Kconfig preflight had required and observed
`CONFIG_STACKPROTECTOR_PER_TASK=y` and
`CONFIG_CC_HAVE_STACKPROTECTOR_SYSREG=y`. After the normal
`target/linux/compile` step, package staging inspected the same intended
kernel tree and found only `CONFIG_STACKPROTECTOR=y`. The package step then
selected the global-canary branch and stopped because `Module.symvers` did
not export `__stack_chk_guard`.

The pinned OpenWrt `target/linux/generic/config-6.18` explicitly contained
`# CONFIG_STACKPROTECTOR_PER_TASK is not set`, while the MT6990 target config
requests stack protection. The integration patch now removes that negative
generic fragment so ARM64 Kconfig can select its supported per-task mode when
the pinned compiler advertises the required sysreg flags. This does not turn
stack protection off. The workflow also uses the exact MT6990 kernel tree
path, and now requires the effective per-task ABI after kernel compilation;
it fails closed instead of silently switching to a different global ABI.
External module flags are derived from the kernel's generated
`TSK_STACK_CANARY` offset.

## Verification status

The source-level unit tests, patch applicability check for the modified
OpenWrt generic config, workflow YAML parse, and `git diff --check` are local
checks. They do not prove the hosted build fix. A new Actions run must show
the post-compile per-task setting and proceed through `package/compile`,
`package/install`, and `target/install` before this issue can be considered
resolved. No firmware build or device installation is claimed here.
