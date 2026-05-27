#!/usr/bin/env python3
"""record_zed_mono_video.py — Record single-eye MP4 from ZED-M.

Auto-detects the ZED-M /dev/videoX node.

Usage:
    python3 record_zed_mono_video.py --out zed_left.mp4 --side left --preview
    python3 record_zed_mono_video.py --out zed_right.mp4 --side right
"""

import argparse
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(__file__))
from find_zed_device import find_zed_device


def parse_args():
    p = argparse.ArgumentParser(description="Record ZED-M mono video.")
    p.add_argument("--out", default="zed_left.mp4", help="Output .mp4 file")
    p.add_argument("--side", choices=["left", "right"], default="left")
    p.add_argument("--device", default="auto")
    p.add_argument("--width", type=int, default=2560)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--preview", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()

    if args.device == "auto":
        try:
            device = find_zed_device()
            print(f"[INFO] ZED-M detected: {device}")
        except RuntimeError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
    else:
        device = args.device

    dev_index = int(device.replace("/dev/video", ""))
    cap = cv2.VideoCapture(dev_index, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    mono_w = actual_w // 2
    mono_h = actual_h

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(args.out, fourcc, float(args.fps), (mono_w, mono_h))
    if not writer.isOpened():
        print("[ERROR] Cannot open VideoWriter. Check output path / codec.", file=sys.stderr)
        cap.release()
        sys.exit(1)

    frame_count = 0
    t_start = time.time()
    print(f"[INFO] Recording {args.side} eye → {args.out}  (Ctrl+C or q to stop)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            w = frame.shape[1]
            mono = frame[:, : w // 2] if args.side == "left" else frame[:, w // 2 :]
            writer.write(mono)
            frame_count += 1

            if args.preview:
                cv2.imshow("ZED-M record (q to stop)", mono)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.time() - t_start
        cap.release()
        writer.release()
        if args.preview:
            cv2.destroyAllWindows()
        fps_actual = frame_count / elapsed if elapsed > 0 else 0
        print(f"[INFO] Recorded {frame_count} frames ({elapsed:.1f}s, {fps_actual:.1f} fps) → {args.out}")


if __name__ == "__main__":
    main()
