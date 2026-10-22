# Verification matrix / 検証記録

Do not upgrade **reported** functionality to **independently verified** without logs, commit and repeatable test procedure.

| Area | Existing developer report | Public independent validation | Next evidence |
| --- | --- | --- | --- |
| Boot chain / Linux 6.18.44 | Kernel boot reported | Pending | Redacted UART log + build metadata |
| OpenWrt userland | Shell reported | Pending | Boot log, filesystem and init checks |
| Ethernet | Link/connectivity reported | Pending | Interface/PHY map, cable test, iperf, reboot |
| Wi-Fi 7 | Operation reported | Pending | PCI enumerations, firmware notices, association/regdomain, stability |
| 5G modem | Not working | Pending | PCI/USB bus map, driver/firmware provenance, logs |
| Slot fallback and recovery | Unresolved for third parties | Pending | Risk-controlled reproducible recovery test |

For a test record, include: revision/serial redacted, date, source commit, image SHA-256, exact commands, expected vs actual behavior, sanitized complete UART/dmesg and a clear pass/fail/unknown conclusion.

Never publish device credentials, factory images, IMEI or extracted signing material.

日本語: 「開発機での報告」と「公開手順による第三者検証」は別列に記録します。
