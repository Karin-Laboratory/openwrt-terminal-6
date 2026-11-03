# Security policy

> **Engineering vs publication:** Unsigned p25/p26 may be built and checked locally or ephemerally in public CI. Do not publish compiled binaries via Actions artifacts, caches, Releases or registries absent a separate rights-cleared distribution decision. Do not publish signing keys, OEM signature-check bypass instructions or device-unique calibration. For Japan-targeted RF operations, a JP domain setting alone does not establish legal authorization: check certification and device/contract terms before transmitting.


This is an experimental source project, **not a secure firmware distribution**.

Report potential vulnerabilities **confidentially** through GitHub Private Vulnerability Reporting when enabled, or contact project maintainers via an already established private channel. Do not put proof-of-concept details, affected input triggers, firmware trust material, device identifiers, private keys or credential contents in public Issues, PRs, commits or CI logs.

For issues affecting vendor products or firmware, coordinate privately with the manufacturer and an appropriate incident coordination organization where warranted. The availability of sample SDK material does not by itself constitute disclosure clearance.

External pull requests must not execute on network-privileged self-hosted builders. Public CI uses only isolated GitHub-hosted runners for independent unit tests; device flashing, signature operations and retained proprietary builds are not included.

Source publication and firmware release have **different security gates**. No factory image, signed partition, radio NV data or default administrative credentials are bundled here.
