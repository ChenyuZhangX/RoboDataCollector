#!/usr/bin/env python3
"""collect_zed_mono_images.py — Capture single-eye JPEG frames from ZED-M.

Auto-detects the ZED-M /dev/videoX node via v4l2-ctl.

Usage:
    python3 collect_zed_mono_images.py --out data/zed_left --side left --preview
    python3 collect_zed_mono_images.py --out data/zed_right --side right
    python3 collect_zed_mono_images.py --out data/zed_left --width 2560 --height 720 --fps 15
"""

import argparse
import os
import sys
import time

import cv2

# Allow running from the project root without installing
sys.path.insert(0, os.path.dirname(__file__))
from find_zed_device import find_zed_device


def parse_args():
    p = argparse.ArgumentParser(description="Capture ZED-M mono images.")
    p.add_argument("--out", default="data/zed_left", help="Output directory")
    p.add_argument("--side", choices=["left", "right"], default="left")
    p.add_argument("--device", default="auto",
                   help="/dev/videoX override, or 'auto'")
    p.add_argument("--width", type=int, default=2560)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--preview", action="store_true",
                   help="Show live preview window (press q to stop)")
    p.add_argument("--quality", type=int, default=95,
                   help="JPEG quality 0-100")
    return p.parse_args()


def main():
    args = parse_args()

    # --- detect device ---
    if args.device == "auto":
        try:
            device = find_zed_device()
            print(f"[INFO] ZED-M detected: {device}")
        except RuntimeError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
    else:
        device = args.device
        print(f"[INFO] Using manually specified device: {device}")

    # --- open capture ---
    dev_index = int(device.replace("/dev/video", ""))
    cap = cv2.VideoCapture(dev_index, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[INFO] Stream: {actual_w}x{actual_h} @ {actual_fps:.1f} fps")

    if actual_w != args.width or actual_h != args.height:
        print(f"[WARN] Requested {args.width}x{args.height} but got {actual_w}x{actual_h}")

    # --- output directory ---
    os.makedirs(args.out, exist_ok=True)

    # --- main loop ---
    frame_idx = 0
    print(f"[INFO] Saving {args.side} eye → {args.out}/  (press Ctrl+C or q to stop)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to grab frame.", file=sys.stderr)
                break

            w = frame.shape[1]
            mono = frame[:, : w // 2] if args.side == "left" else frame[:, w // 2 :]

            ts = time.time()
            fname = os.path.join(args.out, f"{frame_idx:06d}_{ts:.6f}.jpg")
            cv2.imwrite(fname, mono, [cv2.IMWRITE_JPEG_QUALITY, args.quality])
            frame_idx += 1

            if args.preview:
                cv2.imshow("ZED-M preview (q to quit)", mono)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if args.preview:
            cv2.destroyAllWindows()
        print(f"[INFO] Saved {frame_idx} frames to {args.out}/")


if __name__ == "__main__":
    main()
