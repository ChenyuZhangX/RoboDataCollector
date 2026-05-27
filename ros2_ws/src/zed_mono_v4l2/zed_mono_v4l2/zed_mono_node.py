"""zed_mono_node.py — ROS 2 Humble node that publishes one eye of ZED-M via V4L2.

No ZED SDK required.  Uses OpenCV with CAP_V4L2 backend.

Parameters (all override-able at launch with -p key:=value):
    device      (str)   "auto" | "/dev/videoX"
    side        (str)   "left" | "right"            default: "left"
    width       (int)   raw frame width              default: 2560
    height      (int)   raw frame height             default: 720
    fps         (int)   capture framerate            default: 30
    topic       (str)   publish topic                default: /zedm/left/image_raw
    frame_id    (str)   camera frame_id              default: zedm_left_camera

Run:
    ros2 run zed_mono_v4l2 zed_mono_node --ros-args \
        -p device:=auto -p side:=left \
        -p topic:=/zedm/left/image_raw -p frame_id:=zedm_left_camera

    ros2 run zed_mono_v4l2 zed_mono_node --ros-args \
        -p side:=right \
        -p topic:=/zedm/right/image_raw -p frame_id:=zedm_right_camera
"""

import re
import subprocess
import sys

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


# ─────────────────────────────────────────────────────────────────────────────
# ZED-M device detection (inline so the package has no external script dep)
# ─────────────────────────────────────────────────────────────────────────────

def _find_zed_device() -> str:
    try:
        out = subprocess.check_output(
            ["v4l2-ctl", "--list-devices"], text=True, stderr=subprocess.STDOUT
        )
    except FileNotFoundError:
        raise RuntimeError("v4l2-ctl not found — install v4l-utils")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"v4l2-ctl failed: {e.output}")

    for block in re.split(r"\n\n+", out.strip()):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if any(kw in lines[0] for kw in ("ZED-M", "ZED Mini", "ZED")):
            for line in lines[1:]:
                m = re.match(r"(/dev/video\d+)", line)
                if m:
                    return m.group(1)

    raise RuntimeError(
        "ZED-M not found. "
        "Check: lsusb | grep 2b03  and  v4l2-ctl --list-devices"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ROS 2 Node
# ─────────────────────────────────────────────────────────────────────────────

class ZedMonoNode(Node):
    def __init__(self):
        super().__init__("zed_mono_v4l2_node")

        # --- declare parameters ---
        self.declare_parameter("device",   "auto")
        self.declare_parameter("side",     "left")
        self.declare_parameter("width",    2560)
        self.declare_parameter("height",   720)
        self.declare_parameter("fps",      30)
        self.declare_parameter("topic",    "/zedm/left/image_raw")
        self.declare_parameter("frame_id", "zedm_left_camera")

        device   = self.get_parameter("device").value
        side     = self.get_parameter("side").value
        width    = self.get_parameter("width").value
        height   = self.get_parameter("height").value
        fps      = self.get_parameter("fps").value
        topic    = self.get_parameter("topic").value
        frame_id = self.get_parameter("frame_id").value

        if side not in ("left", "right"):
            self.get_logger().error(f"Invalid side '{side}'. Use 'left' or 'right'.")
            rclpy.shutdown()
            return

        # --- detect device ---
        if device == "auto":
            try:
                device = _find_zed_device()
                self.get_logger().info(f"ZED-M auto-detected: {device}")
            except RuntimeError as e:
                self.get_logger().error(str(e))
                rclpy.shutdown()
                return
        else:
            self.get_logger().info(f"Using device: {device}")

        # --- open capture ---
        dev_idx = int(device.replace("/dev/video", ""))
        self._cap = cv2.VideoCapture(dev_idx, cv2.CAP_V4L2)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.get_logger().info(
            f"Stream {actual_w}x{actual_h}, side={side}, publishing on {topic}"
        )

        self._side     = side
        self._frame_id = frame_id
        self._bridge   = CvBridge()

        # --- publisher ---
        self._pub = self.create_publisher(Image, topic, 10)

        # --- timer ---
        period = 1.0 / fps
        self._timer = self.create_timer(period, self._capture_and_publish)

    def _capture_and_publish(self):
        ret, frame = self._cap.read()
        if not ret:
            self.get_logger().warn("Failed to grab frame from ZED-M.")
            return

        w = frame.shape[1]
        mono = frame[:, : w // 2] if self._side == "left" else frame[:, w // 2 :]

        msg = self._bridge.cv2_to_imgmsg(mono, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        self._pub.publish(msg)

    def destroy_node(self):
        if hasattr(self, "_cap") and self._cap.isOpened():
            self._cap.release()
        super().destroy_node()


# ─────────────────────────────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = ZedMonoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
