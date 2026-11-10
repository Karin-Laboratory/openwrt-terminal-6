#!/bin/bash
# SPDX-License-Identifier: MIT
# Real ext4 integration checks using newly-created temporary image files only.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
    echo 'P44_REAL_EXT4_TEST_REQUIRES_ROOT' >&2
    exit 2
fi

repo=$(cd "$(dirname "$0")/.." && pwd)
helper="$repo/tools/boot/prepare_p44_state.sh"
runner="$repo/tools/build/install_p44_extension.py"
tmp=$(mktemp -d "${TMPDIR:-/tmp}/air6-p44-ext4.XXXXXX")
mounts=()
cleanup() {
    for mnt in "${mounts[@]}"; do
        mountpoint -q "$mnt" && umount "$mnt" || :
    done
    rm -rf -- "$tmp"
    if [[ ${overlay_created:-0} == 1 ]]; then rmdir /overlay 2>/dev/null || :; fi
}
trap cleanup EXIT

new_ext4() {
    local image=$1 mount_dir=$2
    truncate -s 64M "$image"
    /usr/sbin/mke2fs -q -F -t ext4 -L AIR6TEST "$image"
    mkdir -p "$mount_dir"
    mount -o loop "$image" "$mount_dir"
    mounts+=("$mount_dir")
}

tree_hash() {
    python3 - "$1" <<'PY'
import hashlib, os, pathlib, stat, sys
root = pathlib.Path(sys.argv[1])
h = hashlib.sha256()
for p in sorted(root.rglob('*')):
    st = p.lstat()
    h.update(p.relative_to(root).as_posix().encode() + b'\0')
    h.update(f'{stat.S_IFMT(st.st_mode)}:{stat.S_IMODE(st.st_mode)}:{st.st_uid}:{st.st_gid}'.encode() + b'\0')
    if p.is_symlink(): h.update(os.fsencode(os.readlink(p)))
    elif p.is_file(): h.update(p.read_bytes())
print(h.hexdigest())
PY
}

expect_code() {
    local expected=$1; shift
    set +e
    "$@"
    local actual=$?
    set -e
    [[ $actual == "$expected" ]] || {
        echo "P44_REAL_EXT4_EXPECTED_EXIT_${expected}_GOT_${actual}" >&2
        return 1
    }
}

# Empty filesystem: read-only preflight must not mutate; RW initialization may
# create only the recognized overlay scaffolding.
new_ext4 "$tmp/empty.img" "$tmp/empty"
before=$(tree_hash "$tmp/empty")
expect_code 2 sh "$helper" "$tmp/empty" check
[[ $(tree_hash "$tmp/empty") == "$before" ]]
sh "$helper" "$tmp/empty" init
sh "$helper" "$tmp/empty" check
[[ -d "$tmp/empty/upper" && -d "$tmp/empty/work" ]]
[[ $(readlink "$tmp/empty/.fs_state") == 2 ]]
umount "$tmp/empty"
mount -o loop,ro,noload "$tmp/empty.img" "$tmp/empty"
expect_code 0 sh "$helper" "$tmp/empty" check
umount "$tmp/empty"
mounts=()
echo P44_REAL_EXT4_EMPTY_INIT_AND_RO_RECHECK_PASS

# Existing recognized overlay: preserve user data byte-for-byte across
# unmount/remount and idempotent init.
new_ext4 "$tmp/existing.img" "$tmp/existing"
mkdir -m 0700 "$tmp/existing/upper" "$tmp/existing/work"
ln -s 2 "$tmp/existing/.fs_state"
printf 'SBA6D_ROOTFS_DATA_V1\n' > "$tmp/existing/.sba6d-rootfs-data-v1"
printf 'owner configuration\n' > "$tmp/existing/upper/config"
before=$(tree_hash "$tmp/existing")
sh "$helper" "$tmp/existing" check
sh "$helper" "$tmp/existing" init
[[ $(tree_hash "$tmp/existing") == "$before" ]]
umount "$tmp/existing"
mount -o loop,ro,noload "$tmp/existing.img" "$tmp/existing"
[[ $(cat "$tmp/existing/upper/config") == 'owner configuration' ]]
[[ $(tree_hash "$tmp/existing") == "$before" ]]
umount "$tmp/existing"
mounts=()
echo P44_REAL_EXT4_EXISTING_OVERLAY_PRESERVED_PASS

# Exact recognized interrupted initialization resumes; unknown/partial state
# is rejected without changing existing bytes.
new_ext4 "$tmp/resume.img" "$tmp/resume"
printf 'AIR6_P44_INIT_IN_PROGRESS_V1\n' > "$tmp/resume/.air6-p44-init-v1"
mkdir -m 0700 "$tmp/resume/upper"
expect_code 3 sh "$helper" "$tmp/resume" check
sh "$helper" "$tmp/resume" init
sh "$helper" "$tmp/resume" check
umount "$tmp/resume"
mounts=()
echo P44_REAL_EXT4_RECOGNIZED_RESUME_PASS

new_ext4 "$tmp/unknown.img" "$tmp/unknown"
printf 'do not overwrite\n' > "$tmp/unknown/owner-data"
before=$(tree_hash "$tmp/unknown")
if sh "$helper" "$tmp/unknown" init 2>/dev/null; then
    echo P44_REAL_EXT4_UNKNOWN_STATE_UNEXPECTEDLY_ACCEPTED >&2
    exit 1
fi
[[ $(tree_hash "$tmp/unknown") == "$before" ]]
umount "$tmp/unknown"
mounts=()
echo P44_REAL_EXT4_UNKNOWN_STATE_STOPPED_UNCHANGED_PASS

# Verify the installed late hook is inert with a real ext4 mount at /overlay
# when its opt-in marker is absent. Use a private mount namespace and refuse to
# shadow any pre-existing host /overlay path or mount.
if mountpoint -q /overlay || [[ -e /overlay || -L /overlay ]]; then
    echo P44_REAL_EXT4_DISABLED_HOOK_TEST_BLOCKED_OVERLAY_PATH_OCCUPIED >&2
    exit 2
fi
mkdir /overlay
overlay_created=1
new_ext4 "$tmp/disabled.img" "$tmp/disabled"
python3 - "$tmp/rootfs" "$runner" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]).parents[0]))
spec_path = Path(sys.argv[2])
root = Path(sys.argv[1]); root.mkdir()
import importlib.util
spec = importlib.util.spec_from_file_location('p44_install', spec_path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.install(root)
PY
# Isolate the temporary bind mount from the host namespace; /overlay exists
# only for the duration of this process and is removed by the EXIT trap.
before=$(tree_hash "$tmp/disabled")
unshare --mount --propagation private bash -c '
    set -euo pipefail
    mount --bind "$1" /overlay
    sh "$2"
    umount /overlay
' _ "$tmp/disabled" "$tmp/rootfs/usr/libexec/air6/p44-extension-runner"
[[ $(tree_hash "$tmp/disabled") == "$before" ]]
echo P44_REAL_EXT4_DISABLED_HOOK_NONINTERFERENCE_PASS
echo P44_REAL_EXT4_INTEGRATION_SUITE_PASS
