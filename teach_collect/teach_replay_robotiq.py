#!/usr/bin/env python3
"""teach_replay_robotiq.py — Teach-and-replay data collection for Franka FR3
with Robotiq 2F-85 gripper, ZED-M wrist camera, and RealSense third-person camera.

Hardware:
  - Franka Research 3 arm  (teach_replay_controller handles motion)
  - Robotiq 2F-85 gripper  (control_msgs/action/GripperCommand)
  - ZED-M wrist camera     (OpenCV + V4L2, auto-detected)
  - RealSense D435          (ROS 2 topic: /camera/color/image_raw)

State machine:
  IDLE → [t] → TEACHING → [s] → READY → [r] → REPLAYING → REVIEW
       ↑______________________________________________|  ([d] discard replay)

Keys during session:
  t   Start teaching (zero-torque mode, drag the arm)
  o   Gripper OPEN    (during teaching)
  c   Gripper CLOSE   (during teaching)
  s   Stop teaching and save trajectory
  r   Replay last teach + record cameras
  1 / s  (after replay) Save this replay
  2 / d  (after replay) Discard this replay, keep teaching data
  3 / r  (after replay) Replay again
  h   Gripper homing
  q   Quit

Output layout (per trajectory, under <output_dir>/<folder>/traj_N/):
  teach/
    joint_trajectory.npz      timestamps, joint_positions [T,7], gripper_cmd [T]
    gripper_events.npz        relative_times, actions ('open'/'close')
    wrist_zed.avi             ZED-M left-eye video during TEACH
    third_rs.avi              RealSense RGB video during TEACH
  replay/
    joint_trajectory.npz      timestamps, joint_positions [T,7]
    joint_velocities.npz      timestamps, velocities [T,7]
    end_effector_pose.npz     timestamps, positions [T,3], quaternions [T,4]
    gripper_events.npz        relative_times, actions
    wrist_zed.avi             ZED-M left-eye video during REPLAY
    third_rs.avi              RealSense RGB video during REPLAY

Usage:
  python3 teach_replay_robotiq.py \\
      --output_dir ~/chenyu/data_collection/data \\
      --fps 30 \\
      --record_rate 100 \\
      --realsense_topic /camera/color/image_raw

  Disable cameras:
      --no_wrist_camera --no_third_camera

  Manual ZED device:
      --zed_device /dev/video4
"""

import argparse
import os
import re
import select
import subprocess
import sys
import termios
import threading
import time
import tty
from pathlib import Path

import cv2
import numpy as np
import rclpy
from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Duration as DurationMsg
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image, JointState
from std_msgs.msg import Bool, String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

try:
    from cv_bridge import CvBridge
    HAVE_CV_BRIDGE = True
except ImportError:
    HAVE_CV_BRIDGE = False

try:
    from control_msgs.action import GripperCommand
    HAVE_GRIPPER = True
except ImportError:
    HAVE_GRIPPER = False
    print("[WARN] control_msgs not available — gripper keys disabled")

try:
    from franka_msgs.msg import FrankaRobotState
    HAVE_FRANKA_STATE = True
except ImportError:
    HAVE_FRANKA_STATE = False
    print("[WARN] franka_msgs not available — EE pose recording disabled")


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
ARM_JOINTS = [f"fr3_joint{i}" for i in range(1, 8)]
TRAJ_DIR_RE = re.compile(r"^traj_(\d+)$")

GRIPPER_OPEN_POS  = 0.0    # Robotiq 2F-85: 0 = fully open
GRIPPER_CLOSE_POS = 0.085  # Robotiq 2F-85: 0.085 = fully closed (85 mm stroke)
GRIPPER_EFFORT    = 50.0   # max_effort [N] — adjust as needed

VIDEO_CODEC = "XVID"       # works without extra codec installation
VIDEO_EXT   = ".avi"


# ─────────────────────────────────────────────────────────────────────────────
# ZED-M auto-detection
# ─────────────────────────────────────────────────────────────────────────────

def find_zed_device() -> str:
    try:
        out = subprocess.check_output(
            ["v4l2-ctl", "--list-devices"], text=True, stderr=subprocess.STDOUT
        )
    except FileNotFoundError:
        raise RuntimeError("v4l2-ctl not found — sudo apt install v4l-utils")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"v4l2-ctl failed: {e.output}")

    for block in re.split(r"\n\n+", out.strip()):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if any(k in lines[0] for k in ("ZED-M", "ZED Mini", "ZED")):
            for line in lines[1:]:
                m = re.match(r"(/dev/video\d+)", line)
                if m:
                    return m.group(1)
    raise RuntimeError(
        "ZED-M not found. Check: lsusb | grep 2b03  and  v4l2-ctl --list-devices"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ZED-M background camera thread
# ─────────────────────────────────────────────────────────────────────────────

class ZedWristCamera:
    """Continuously reads ZED-M frames in a background thread.

    Call start_recording(path) / stop_recording() to write AVI.
    Call get_latest() for the current BGR frame.
    """

    def __init__(self, device: str, width=2560, height=720, fps=30, side="left"):
        self._side  = side
        self._fps   = fps
        self._mono_w = width // 2
        self._mono_h = height

        dev_idx = int(device.replace("/dev/video", ""))
        self._cap = cv2.VideoCapture(dev_idx, cv2.CAP_V4L2)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)

        self._lock         = threading.Lock()
        self._latest_frame = None
        self._latest_ts    = None

        self._writer       = None
        self._writer_lock  = threading.Lock()

        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.005)
                continue
            w = frame.shape[1]
            mono = frame[:, : w // 2] if self._side == "left" else frame[:, w // 2 :]
            ts = time.time()
            with self._lock:
                self._latest_frame = mono
                self._latest_ts    = ts
            with self._writer_lock:
                if self._writer is not None:
                    self._writer.write(mono)

    def start_recording(self, path: str):
        fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
        with self._writer_lock:
            self._writer = cv2.VideoWriter(
                path, fourcc, self._fps, (self._mono_w, self._mono_h)
            )

    def stop_recording(self):
        with self._writer_lock:
            if self._writer is not None:
                self._writer.release()
                self._writer = None

    def get_latest(self):
        with self._lock:
            return self._latest_frame, self._latest_ts

    def close(self):
        self._running = False
        self._thread.join(timeout=2.0)
        self.stop_recording()
        self._cap.release()


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator node
# ─────────────────────────────────────────────────────────────────────────────

class TeachReplayRobotiq(Node):

    STATE_IDLE      = "IDLE"
    STATE_TEACHING  = "TEACHING"
    STATE_READY     = "READY"
    STATE_REPLAYING = "REPLAYING"
    STATE_REVIEW    = "REVIEW"

    def __init__(self, args):
        super().__init__("teach_replay_robotiq")

        self._args = args
        self._fps         = args.fps
        self._record_rate = args.record_rate
        self._smooth_win  = args.trajectory_smoothing_window
        self._output_dir  = Path(args.output_dir).expanduser()
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._save_folder = self._prompt_folder()
        self._next_traj   = self._get_next_index()

        # State
        self.state       = self.STATE_IDLE
        self._sess_dir   = None
        self._state_lock = threading.Lock()

        # Joint / EE cache
        self._arm_q      = None   # [7]
        self._arm_dq     = None   # [7]
        self._ee_pose    = None   # [7]: x y z qx qy qz qw
        self._gripper_w  = 0.0   # commanded gripper position

        # Teach buffers
        self._teach_t0      = None
        self._teach_times   = []
        self._teach_q       = []
        self._teach_gw      = []   # gripper commanded pos at each sample
        self._teach_events  = []   # [(rel_time, 'open'/'close')]

        # Replay buffers
        self._replay_t0       = None
        self._replay_times    = []
        self._replay_q        = []
        self._replay_dq_times = []
        self._replay_dq       = []
        self._replay_ee_times = []
        self._replay_ee_pose  = []
        self._replay_events   = []
        self._recorded_traj   = None  # saved after teach: (times, q, events)

        # Camera bridge
        self._bridge = CvBridge() if HAVE_CV_BRIDGE else None

        # ZED-M wrist camera
        self._zed = None
        if not args.no_wrist_camera:
            self._init_zed()

        # RealSense latest frame
        self._rs_frame     = None
        self._rs_ts        = None
        self._rs_lock      = threading.Lock()
        self._rs_writer    = None
        self._rs_writer_lock = threading.Lock()

        # ROS interfaces
        qos = 10
        self._mode_pub = self.create_publisher(String, "/teach_replay/mode", qos)
        self._traj_pub = self.create_publisher(
            JointTrajectory, "/teach_replay/trajectory", qos
        )
        self.create_subscription(JointState, "/joint_states", self._js_cb, qos)

        if HAVE_FRANKA_STATE:
            self.create_subscription(
                FrankaRobotState,
                "/franka_robot_state_broadcaster/robot_state",
                self._franka_state_cb, qos,
            )

        self.create_subscription(
            Bool, "/teach_replay/replay_started",  self._replay_started_cb, qos
        )
        self.create_subscription(
            Bool, "/teach_replay/replay_finished", self._replay_finished_cb, qos
        )

        # RealSense topic
        if not args.no_third_camera and HAVE_CV_BRIDGE:
            topic = args.realsense_topic
            if topic.endswith("/compressed"):
                self.create_subscription(
                    CompressedImage, topic, self._rs_compressed_cb, qos_profile_sensor_data
                )
            else:
                self.create_subscription(
                    Image, topic, self._rs_raw_cb, qos_profile_sensor_data
                )
            self.get_logger().info(f"RealSense topic: {topic}")

        # Robotiq gripper action client
        self._gripper_client = None
        if HAVE_GRIPPER:
            self._gripper_client = ActionClient(
                self, GripperCommand, "/robotiq_gripper_controller/gripper_cmd"
            )
            self.get_logger().info("Robotiq gripper client ready")

        # Recording timer
        self._rec_timer = self.create_timer(1.0 / self._record_rate, self._record_tick)

        # Keyboard thread
        threading.Thread(target=self._keyboard_loop, daemon=True).start()

        self._print_help()

    # ─── ZED-M init ──────────────────────────────────────────────────────────

    def _init_zed(self):
        dev = self._args.zed_device
        if dev == "auto":
            try:
                dev = find_zed_device()
                self.get_logger().info(f"ZED-M auto-detected: {dev}")
            except RuntimeError as e:
                self.get_logger().warn(f"ZED-M not found, wrist camera disabled: {e}")
                return
        else:
            self.get_logger().info(f"ZED-M device: {dev}")
        try:
            self._zed = ZedWristCamera(dev, side=self._args.zed_side, fps=self._fps)
            self.get_logger().info("ZED-M wrist camera started.")
        except Exception as e:
            self.get_logger().warn(f"ZED-M init failed: {e}")
            self._zed = None

    # ─── Subscriptions ───────────────────────────────────────────────────────

    def _js_cb(self, msg: JointState):
        q  = [None] * 7
        dq = [None] * 7
        for i, name in enumerate(msg.name):
            if i < len(msg.position):
                try:
                    idx = ARM_JOINTS.index(name)
                    q[idx]  = msg.position[i]
                    if msg.velocity:
                        dq[idx] = msg.velocity[i]
                except ValueError:
                    pass
        if all(v is not None for v in q):
            self._arm_q  = np.array(q,  dtype=np.float64)
        if all(v is not None for v in dq):
            self._arm_dq = np.array(dq, dtype=np.float64)

    def _franka_state_cb(self, msg):
        try:
            p = msg.o_t_ee_c  # 4×4 column-major
            if len(p) >= 16:
                t = np.array([p[12], p[13], p[14]])
                # Rotation → quaternion via scipy (optional) or manual
                R = np.array([
                    [p[0], p[4], p[8]],
                    [p[1], p[5], p[9]],
                    [p[2], p[6], p[10]],
                ])
                qw = 0.5 * np.sqrt(max(0, 1 + R[0,0] + R[1,1] + R[2,2]))
                if qw > 1e-6:
                    qx = (R[2,1] - R[1,2]) / (4 * qw)
                    qy = (R[0,2] - R[2,0]) / (4 * qw)
                    qz = (R[1,0] - R[0,1]) / (4 * qw)
                else:
                    qx = qy = qz = 0.0
                self._ee_pose = np.array([t[0], t[1], t[2], qx, qy, qz, qw])
        except Exception:
            pass

    def _rs_raw_cb(self, msg: Image):
        if self._bridge is None:
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            ts = time.time()
            with self._rs_lock:
                self._rs_frame = frame
                self._rs_ts    = ts
            with self._rs_writer_lock:
                if self._rs_writer is not None:
                    self._rs_writer.write(frame)
        except Exception:
            pass

    def _rs_compressed_cb(self, msg: CompressedImage):
        try:
            arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                return
            ts = time.time()
            with self._rs_lock:
                self._rs_frame = frame
                self._rs_ts    = ts
            with self._rs_writer_lock:
                if self._rs_writer is not None:
                    self._rs_writer.write(frame)
        except Exception:
            pass

    def _replay_started_cb(self, msg: Bool):
        if msg.data:
            self.get_logger().info("Replay started signal received.")
            self._replay_t0 = time.time()

    def _replay_finished_cb(self, msg: Bool):
        if msg.data and self.state == self.STATE_REPLAYING:
            self.get_logger().info("Replay finished signal received.")
            self._finish_replay()

    # ─── Recording timer ─────────────────────────────────────────────────────

    def _record_tick(self):
        if self.state == self.STATE_TEACHING and self._teach_t0 is not None:
            if self._arm_q is not None:
                self._teach_times.append(time.time() - self._teach_t0)
                self._teach_q.append(self._arm_q.copy())
                self._teach_gw.append(self._gripper_w)

        elif self.state == self.STATE_REPLAYING and self._replay_t0 is not None:
            now = time.time()
            if self._arm_q is not None:
                self._replay_times.append(now - self._replay_t0)
                self._replay_q.append(self._arm_q.copy())
            if self._arm_dq is not None:
                self._replay_dq_times.append(now - self._replay_t0)
                self._replay_dq.append(self._arm_dq.copy())
            if self._ee_pose is not None:
                self._replay_ee_times.append(now - self._replay_t0)
                self._replay_ee_pose.append(self._ee_pose.copy())

    # ─── Keyboard ────────────────────────────────────────────────────────────

    def _keyboard_loop(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while rclpy.ok():
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    ch = sys.stdin.read(1).lower()
                    self._handle_key(ch)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def _handle_key(self, ch):
        if ch == "q":
            self.get_logger().info("Quitting…")
            rclpy.shutdown()

        elif ch == "t" and self.state == self.STATE_IDLE:
            self._start_teach()

        elif ch == "o" and self.state == self.STATE_TEACHING:
            self._gripper_send(GRIPPER_OPEN_POS, "open")

        elif ch == "c" and self.state == self.STATE_TEACHING:
            self._gripper_send(GRIPPER_CLOSE_POS, "close")

        elif ch == "s" and self.state == self.STATE_TEACHING:
            self._stop_teach_save()

        elif ch == "r" and self.state == self.STATE_READY:
            self._start_replay()

        elif ch in ("1", "s") and self.state == self.STATE_REVIEW:
            self._save_replay()

        elif ch in ("2", "d") and self.state == self.STATE_REVIEW:
            self._discard_replay()

        elif ch in ("3", "r") and self.state == self.STATE_REVIEW:
            self._replay_again()

        elif ch == "h":
            self._gripper_home()

    # ─── Gripper helpers ─────────────────────────────────────────────────────

    def _gripper_send(self, position: float, label: str):
        if not HAVE_GRIPPER or self._gripper_client is None:
            self.get_logger().warn("Gripper not available.")
            return
        goal = GripperCommand.Goal()
        goal.command.position   = position
        goal.command.max_effort = GRIPPER_EFFORT
        self._gripper_client.send_goal_async(goal)
        self._gripper_w = position
        self.get_logger().info(f"Gripper → {label} ({position:.3f} m)")
        if self._teach_t0 is not None:
            rel = time.time() - self._teach_t0
            self._teach_events.append((rel, label))

    def _gripper_home(self):
        """Send gripper to open (home) position."""
        self._gripper_send(GRIPPER_OPEN_POS, "home/open")

    # ─── TEACH ───────────────────────────────────────────────────────────────

    def _start_teach(self):
        if self._arm_q is None:
            self.get_logger().warn("No joint state received yet. Retry.")
            return

        self._sess_dir = self._new_traj_dir()
        (self._sess_dir / "teach").mkdir()
        (self._sess_dir / "replay").mkdir()

        # Clear teach buffers
        self._teach_t0     = time.time()
        self._teach_times  = []
        self._teach_q      = []
        self._teach_gw     = []
        self._teach_events = []

        # Start camera recording for TEACH phase
        if self._zed:
            path = str(self._sess_dir / "teach" / f"wrist_zed{VIDEO_EXT}")
            self._zed.start_recording(path)
        self._start_rs_recording(str(self._sess_dir / "teach" / f"third_rs{VIDEO_EXT}"))

        # Switch controller to TEACH mode (zero torques)
        self._pub_mode("teach")
        self.state = self.STATE_TEACHING
        self.get_logger().info(
            "TEACHING started. Drag the arm. "
            "'o'=open gripper  'c'=close gripper  's'=save & stop"
        )

    def _stop_teach_save(self):
        if not self._teach_times:
            self.get_logger().warn("No data recorded. Keep teaching.")
            return

        # Stop cameras
        if self._zed:
            self._zed.stop_recording()
        self._stop_rs_recording()

        # Switch controller back to idle
        self._pub_mode("idle")

        # Smooth and save
        self._save_teach_data()
        self.state = self.STATE_READY
        self.get_logger().info(
            f"Teaching saved ({len(self._teach_times)} samples). "
            "Press 'r' to replay."
        )

    def _save_teach_data(self):
        times = np.array(self._teach_times, dtype=np.float64)
        q_arr = np.array(self._teach_q,     dtype=np.float32)
        gw    = np.array(self._teach_gw,    dtype=np.float32)

        # Smooth joint positions
        if self._smooth_win > 1 and len(times) > self._smooth_win:
            from scipy.signal import savgol_filter
            try:
                q_arr = savgol_filter(q_arr, self._smooth_win, 3, axis=0)
            except ImportError:
                pass

        np.savez_compressed(
            self._sess_dir / "teach" / "joint_trajectory.npz",
            timestamps=times,
            joint_positions=q_arr,
            gripper_cmd=gw,
        )

        rel_times = np.array([e[0] for e in self._teach_events], dtype=np.float64)
        actions   = np.array([e[1] for e in self._teach_events], dtype=object)
        np.savez_compressed(
            self._sess_dir / "teach" / "gripper_events.npz",
            relative_times=rel_times,
            actions=actions,
        )

        # Keep for replay
        self._recorded_traj = (times, q_arr, self._teach_events.copy())

    # ─── REPLAY ──────────────────────────────────────────────────────────────

    def _start_replay(self):
        if self._recorded_traj is None:
            self.get_logger().warn("No teach data. Press 't' to teach first.")
            return

        times, q_arr, events = self._recorded_traj

        # Clear replay buffers
        self._replay_t0       = None   # set when replay_started signal arrives
        self._replay_times    = []
        self._replay_q        = []
        self._replay_dq_times = []
        self._replay_dq       = []
        self._replay_ee_times = []
        self._replay_ee_pose  = []
        self._replay_events   = list(events)

        # Start camera recording for REPLAY phase
        if self._zed:
            path = str(self._sess_dir / "replay" / f"wrist_zed{VIDEO_EXT}")
            self._zed.start_recording(path)
        self._start_rs_recording(str(self._sess_dir / "replay" / f"third_rs{VIDEO_EXT}"))

        # Build JointTrajectory message
        traj_msg = self._build_trajectory(times, q_arr)

        # Switch to replay mode
        self._pub_mode("replay")
        time.sleep(0.05)
        self._traj_pub.publish(traj_msg)

        # Schedule gripper events
        self._schedule_gripper_events(events)

        self.state = self.STATE_REPLAYING
        self.get_logger().info("REPLAYING… (waiting for replay_started signal)")

    def _build_trajectory(self, times, q_arr) -> JointTrajectory:
        msg = JointTrajectory()
        msg.joint_names = ARM_JOINTS

        t0 = times[0]
        for i in range(len(times)):
            pt = JointTrajectoryPoint()
            pt.positions = q_arr[i].tolist()
            dt = float(times[i] - t0)
            pt.time_from_start = DurationMsg(
                sec=int(dt), nanosec=int((dt % 1) * 1e9)
            )
            msg.points.append(pt)
        return msg

    def _schedule_gripper_events(self, events):
        for rel_time, action in events:
            def _fire(action=action, rel_time=rel_time):
                # Wait until replay_t0 is set, then sleep to the right time
                deadline = rel_time
                while self._replay_t0 is None:
                    time.sleep(0.01)
                fire_at = self._replay_t0 + deadline
                delay = fire_at - time.time()
                if delay > 0:
                    time.sleep(delay)
                pos = GRIPPER_OPEN_POS if action == "open" else GRIPPER_CLOSE_POS
                self._gripper_send(pos, action)
                self._replay_events.append((time.time() - self._replay_t0, action))

            t = threading.Thread(target=_fire, daemon=True)
            t.start()

    def _finish_replay(self):
        if self._zed:
            self._zed.stop_recording()
        self._stop_rs_recording()
        self._pub_mode("idle")
        self._save_replay_data()
        self.state = self.STATE_REVIEW
        self.get_logger().info(
            "Replay finished. Press: 1=save  2=discard  3=replay-again"
        )

    def _save_replay_data(self):
        times = np.array(self._replay_times,    dtype=np.float64)
        q_arr = np.array(self._replay_q,        dtype=np.float32)
        np.savez_compressed(
            self._sess_dir / "replay" / "joint_trajectory.npz",
            timestamps=times, joint_positions=q_arr,
        )
        if self._replay_dq:
            np.savez_compressed(
                self._sess_dir / "replay" / "joint_velocities.npz",
                timestamps=np.array(self._replay_dq_times, dtype=np.float64),
                velocities=np.array(self._replay_dq, dtype=np.float32),
            )
        if self._replay_ee_pose:
            ee = np.array(self._replay_ee_pose, dtype=np.float32)
            np.savez_compressed(
                self._sess_dir / "replay" / "end_effector_pose.npz",
                timestamps=np.array(self._replay_ee_times, dtype=np.float64),
                positions=ee[:, :3],
                quaternions=ee[:, 3:],
            )
        rel  = np.array([e[0] for e in self._replay_events], dtype=np.float64)
        acts = np.array([e[1] for e in self._replay_events], dtype=object)
        np.savez_compressed(
            self._sess_dir / "replay" / "gripper_events.npz",
            relative_times=rel, actions=acts,
        )

    def _save_replay(self):
        self.get_logger().info(f"Saved: {self._sess_dir}")
        self._reset_for_next()

    def _discard_replay(self):
        # Remove only replay/ files, keep teach/
        import shutil
        replay_dir = self._sess_dir / "replay"
        shutil.rmtree(replay_dir)
        replay_dir.mkdir()
        self.get_logger().info("Replay discarded. Press 'r' to replay again.")
        self.state = self.STATE_READY

    def _replay_again(self):
        import shutil
        shutil.rmtree(self._sess_dir / "replay")
        (self._sess_dir / "replay").mkdir()
        self.get_logger().info("Re-running replay…")
        self.state = self.STATE_READY
        self._start_replay()

    def _reset_for_next(self):
        self._sess_dir      = None
        self._recorded_traj = None
        self.state = self.STATE_IDLE
        self.get_logger().info("Ready for next trajectory. Press 't' to teach.")

    # ─── RealSense video writer ───────────────────────────────────────────────

    def _start_rs_recording(self, path: str):
        if self._args.no_third_camera or not HAVE_CV_BRIDGE:
            return
        with self._rs_lock:
            frame = self._rs_frame
        if frame is None:
            self.get_logger().warn("No RealSense frame yet — skipping RS recording.")
            return
        h, w = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
        with self._rs_writer_lock:
            self._rs_writer = cv2.VideoWriter(path, fourcc, self._fps, (w, h))

    def _stop_rs_recording(self):
        with self._rs_writer_lock:
            if self._rs_writer is not None:
                self._rs_writer.release()
                self._rs_writer = None

    # ─── ROS mode publisher ───────────────────────────────────────────────────

    def _pub_mode(self, mode: str):
        msg = String()
        msg.data = mode
        self._mode_pub.publish(msg)

    # ─── Directory helpers ────────────────────────────────────────────────────

    def _prompt_folder(self) -> Path:
        while True:
            name = input("Enter save folder name: ").strip()
            if name and "/" not in name:
                p = self._output_dir / name
                p.mkdir(parents=True, exist_ok=True)
                return p
            print("Please enter a simple folder name (no slashes).")

    def _get_next_index(self) -> int:
        indices = [
            int(m.group(1))
            for d in self._save_folder.iterdir()
            if d.is_dir() and (m := TRAJ_DIR_RE.match(d.name))
        ]
        return max(indices, default=-1) + 1

    def _new_traj_dir(self) -> Path:
        while True:
            p = self._save_folder / f"traj_{self._next_traj}"
            self._next_traj += 1
            if not p.exists():
                p.mkdir(parents=True)
                self.get_logger().info(f"Trajectory dir: {p}")
                return p

    # ─── Help ────────────────────────────────────────────────────────────────

    def _print_help(self):
        self.get_logger().info("=" * 60)
        self.get_logger().info("Teach-Replay Robotiq — Keys:")
        self.get_logger().info("  t : start teaching (drag the arm)")
        self.get_logger().info("  o : gripper OPEN   (during teach)")
        self.get_logger().info("  c : gripper CLOSE  (during teach)")
        self.get_logger().info("  s : stop + save teach trajectory")
        self.get_logger().info("  r : replay + record cameras")
        self.get_logger().info("  after replay → 1=save  2=discard  3=replay-again")
        self.get_logger().info("  h : gripper home (open)")
        self.get_logger().info("  q : quit")
        self.get_logger().info("=" * 60)

    def destroy_node(self):
        if self._zed:
            self._zed.close()
        self._stop_rs_recording()
        super().destroy_node()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Teach-replay data collection.")
    p.add_argument("--output_dir",   default="~/chenyu/data_collection/data")
    p.add_argument("--fps",          type=int,   default=30)
    p.add_argument("--record_rate",  type=int,   default=100)
    p.add_argument("--trajectory_smoothing_window", type=int, default=11)
    p.add_argument("--realsense_topic", default="/camera/color/image_raw")
    p.add_argument("--zed_device",   default="auto")
    p.add_argument("--zed_side",     choices=["left", "right"], default="left")
    p.add_argument("--no_wrist_camera",  action="store_true")
    p.add_argument("--no_third_camera",  action="store_true")
    return p.parse_args(argv)


def main():
    argv = sys.argv[1:]
    # Separate ROS args from script args
    ros_argv, script_argv = [], []
    skip = False
    for i, a in enumerate(argv):
        if a == "--ros-args":
            ros_argv = argv[i:]
            break
        script_argv.append(a)

    args = parse_args(script_argv)
    rclpy.init(args=ros_argv if ros_argv else None)
    node = TeachReplayRobotiq(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
