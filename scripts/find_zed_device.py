"""find_zed_device.py — Auto-detect the first /dev/videoX node of a ZED-M camera.

Usage as library:
    from find_zed_device import find_zed_device
    dev = find_zed_device()          # e.g. "/dev/video6"

Usage as script:
    python3 find_zed_device.py       # prints device path or exits with error
"""

import re
import subprocess
import sys


def find_zed_device() -> str:
    """Return the first /dev/videoX node belonging to ZED-M.

    Raises RuntimeError when no device is found.
    """
    try:
        output = subprocess.check_output(
            ["v4l2-ctl", "--list-devices"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "v4l2-ctl not found. Install it with: sudo apt install v4l-utils"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"v4l2-ctl failed: {e.output}")

    # Each device block is separated by a blank line; the first line of a block
    # is the device name.  We look for blocks whose name contains "ZED".
    for block in re.split(r"\n\n+", output.strip()):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        header = lines[0]
        if not any(kw in header for kw in ("ZED-M", "ZED Mini", "ZED")):
            continue
        for line in lines[1:]:
            m = re.match(r"(/dev/video\d+)", line)
            if m:
                return m.group(1)

    raise RuntimeError(
        "ZED-M video device not found.\n"
        "Checks:\n"
        "  lsusb | grep -i -E 'zed|stereo|2b03'\n"
        "  v4l2-ctl --list-devices\n"
        "  ID 2b03:f682 must appear (video interface); f681 alone = HID only.\n"
        "  Use a USB3 port, USB3 cable, no passive hub."
    )


if __name__ == "__main__":
    try:
        print(find_zed_device())
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
