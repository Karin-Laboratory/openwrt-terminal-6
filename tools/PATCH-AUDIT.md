# Read-only patch applicability checker

This is a public, stand-alone development tool and **not** a compiled kernel patch or device firmware.

Usage with legally obtained, text-only patches and a git-managed kernel checkout:

```sh
python3 tools/check_patch_series.py --source /path/to/linux /path/to/0001-example.patch
```

It runs `git apply --check` and `git apply --reverse --check`, never applies changes, and prints JSON with patch SHA-256 and a candidate status. The commands may inspect the checkout and the patch but do not write device partitions. Patches may have dependencies or require earlier patches in the series; a conflict does not prove the patch itself is wrong.

**Limitations:** This tool does not assess code copyrights, verify firmware signatures, rebuild a kernel or validate hardware compatibility. Do not feed it private vendor dumps or treat its output as approval to flash.
