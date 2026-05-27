#!/usr/bin/env bash
# Auto-detect the first /dev/videoX node belonging to a ZED-M camera.
# Usage: source this file or run directly.  Exit code 0 → device printed to stdout.

set -e

DEVICE=$(v4l2-ctl --list-devices 2>/dev/null | awk '
/ZED-M|ZED Mini|ZED/ { found=1; next }
found && /\/dev\/video/ { print $1; exit }
/^[^ \t]/ { found=0 }
')

if [ -z "$DEVICE" ]; then
    echo "ERROR: ZED-M video device not found." >&2
    echo "Please check:" >&2
    echo "  1. lsusb | grep -i -E 'zed|stereo|2b03'" >&2
    echo "  2. v4l2-ctl --list-devices" >&2
    echo "  3. whether ID 2b03:f682 STEREOLABS ZED-M camera exists in lsusb" >&2
    echo "  4. USB3 port, USB3 cable, no passive hub" >&2
    exit 1
fi

echo "$DEVICE"
