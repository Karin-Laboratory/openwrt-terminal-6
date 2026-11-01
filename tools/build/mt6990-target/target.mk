# SPDX-License-Identifier: GPL-2.0-only
# Standalone MT6990 research subtarget only; not a device/firmware profile.
ARCH:=aarch64
SUBTARGET:=mt6990
BOARDNAME:=MediaTek MT6990 (source-only research)
CPU_TYPE:=cortex-a55
KERNELNAME:=Image dtbs
DEFAULT_PACKAGES += procd ubus uci netifd dropbear
define Target/Description
  Noninstallable MT6990 source-build bootstrap; no Air6 device images.
endef
