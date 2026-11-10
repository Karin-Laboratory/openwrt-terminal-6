#!/bin/sh
# SPDX-License-Identifier: MIT
# Check or safely initialize overlay scaffolding on an already mounted ext4.
# This never formats, repairs, truncates, or removes data from the filesystem.
set -eu

fail() {
    echo "AIR6_P44_STATE_BLOCKED_$1" >&2
    exit 1
}

is_real_dir() {
    [ -d "$1" ] && [ ! -L "$1" ]
}

is_empty_dir() {
    empty_dir=$1
    is_real_dir "$empty_dir" || return 1
    for empty_item in "$empty_dir"/* "$empty_dir"/.[!.]* "$empty_dir"/..?*; do
        [ -e "$empty_item" ] || [ -L "$empty_item" ] || continue
        return 1
    done
    return 0
}

root_empty_or_lost_found() {
    root_scan_dir=$1
    is_real_dir "$root_scan_dir" || return 1
    for root_scan_item in "$root_scan_dir"/* "$root_scan_dir"/.[!.]* "$root_scan_dir"/..?*; do
        [ -e "$root_scan_item" ] || [ -L "$root_scan_item" ] || continue
        if [ "$root_scan_item" = "$root_scan_dir/lost+found" ] && is_empty_dir "$root_scan_item"; then
            continue
        fi
        return 1
    done
    return 0
}

has_exact_line() {
    exact_file=$1
    exact_expected=$2
    [ -f "$exact_file" ] && [ ! -L "$exact_file" ] || return 1
    [ "$(grep -Fxc "$exact_expected" "$exact_file" 2>/dev/null || :)" = 1 ] || return 1
    ! grep -Fxv "$exact_expected" "$exact_file" >/dev/null 2>&1
}

is_ready() {
    ready_dir=$1
    has_exact_line "$ready_dir/.sba6d-rootfs-data-v1" "SBA6D_ROOTFS_DATA_V1" || return 1
    is_real_dir "$ready_dir/upper" || return 1
    is_real_dir "$ready_dir/work" || return 1
    [ -L "$ready_dir/.fs_state" ] && [ "$(readlink "$ready_dir/.fs_state")" = 2 ]
}

is_transaction() {
    transaction_dir=$1
    has_exact_line "$transaction_dir/.air6-p44-init-v1" "AIR6_P44_INIT_IN_PROGRESS_V1" || return 1
    root_empty_or_lost_found_except_transaction "$transaction_dir"
}

root_empty_or_lost_found_except_transaction() {
    transaction_scan_dir=$1
    is_real_dir "$transaction_scan_dir" || return 1
    for transaction_scan_item in "$transaction_scan_dir"/* "$transaction_scan_dir"/.[!.]* "$transaction_scan_dir"/..?*; do
        [ -e "$transaction_scan_item" ] || [ -L "$transaction_scan_item" ] || continue
        case "$transaction_scan_item" in
            "$transaction_scan_dir/.air6-p44-init-v1")
                has_exact_line "$transaction_scan_item" "AIR6_P44_INIT_IN_PROGRESS_V1" || return 1
                ;;
            "$transaction_scan_dir/upper"|"$transaction_scan_dir/work")
                is_empty_dir "$transaction_scan_item" || return 1
                ;;
            "$transaction_scan_dir/.fs_state")
                [ -L "$transaction_scan_item" ] && [ "$(readlink "$transaction_scan_item")" = 2 ] || return 1
                ;;
            "$transaction_scan_dir/.sba6d-rootfs-data-v1")
                has_exact_line "$transaction_scan_item" "SBA6D_ROOTFS_DATA_V1" || return 1
                ;;
            "$transaction_scan_dir/lost+found")
                is_empty_dir "$transaction_scan_item" || return 1
                ;;
            *)
                return 1
                ;;
        esac
    done
    return 0
}

write_exclusive_marker() {
    marker_file=$1
    marker_value=$2
    ( set -C; printf '%s\n' "$marker_value" > "$marker_file" )
}

init() {
    init_dir=$1
    if is_ready "$init_dir"; then
        echo AIR6_P44_EXISTING_STATE_PRESERVED
        return 0
    fi
    if root_empty_or_lost_found "$init_dir"; then
        write_exclusive_marker "$init_dir/.air6-p44-init-v1" "AIR6_P44_INIT_IN_PROGRESS_V1" ||
            fail INITIALIZATION_MARKER
        sync
    elif is_transaction "$init_dir"; then
        : # Resume only the exact, non-destructive layout created by this helper.
    else
        fail NOT_EMPTY_OR_RECOGNIZED_TRANSACTION
    fi

    if [ ! -e "$init_dir/upper" ] && [ ! -L "$init_dir/upper" ]; then
        (umask 077; mkdir "$init_dir/upper") || fail UPPER_CREATE
    fi
    is_empty_dir "$init_dir/upper" || fail UPPER_UNEXPECTED_CONTENT

    if [ ! -e "$init_dir/work" ] && [ ! -L "$init_dir/work" ]; then
        (umask 077; mkdir "$init_dir/work") || fail WORK_CREATE
    fi
    is_empty_dir "$init_dir/work" || fail WORK_UNEXPECTED_CONTENT

    if [ ! -e "$init_dir/.fs_state" ] && [ ! -L "$init_dir/.fs_state" ]; then
        ln -s 2 "$init_dir/.fs_state" || fail FS_STATE_CREATE
    fi
    [ -L "$init_dir/.fs_state" ] && [ "$(readlink "$init_dir/.fs_state")" = 2 ] ||
        fail FS_STATE_INVALID

    if [ ! -e "$init_dir/.sba6d-rootfs-data-v1" ] &&
       [ ! -L "$init_dir/.sba6d-rootfs-data-v1" ]; then
        write_exclusive_marker "$init_dir/.sba6d-rootfs-data-v1" "SBA6D_ROOTFS_DATA_V1" ||
            fail READY_MARKER_CREATE
    fi
    sync
    is_ready "$init_dir" || fail POST_INITIALIZATION_CHECK
    echo AIR6_P44_EMPTY_EXT4_INITIALIZED
}

dir=${1:-}
action=${2:-}
case "$action" in
    check)
        is_ready "$dir" && { echo AIR6_P44_READY; exit 0; }
        if root_empty_or_lost_found "$dir"; then
            echo AIR6_P44_EMPTY_EXT4
            exit 2
        fi
        if is_transaction "$dir"; then
            echo AIR6_P44_INITIALIZATION_RESUMABLE
            exit 3
        fi
        fail UNKNOWN_OR_PARTIAL_STATE
        ;;
    init)
        init "$dir"
        ;;
    *)
        fail "USAGE_EXPECTED_MOUNTPOINT_AND_CHECK_OR_INIT"
        ;;
esac
