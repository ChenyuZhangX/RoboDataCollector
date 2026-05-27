# Data Collection - Technical Reference

**For:** Understanding DROID data formats, structures, and processing pipeline  
**Audience:** Developers, ML engineers, data pipeline builders

---

## System Architecture

### Data Flow

```
Physical Robot + Oculus VR
        ↓
    RobotEnv (gym.Env wrapper)
        ├─ libfranka (low-level arm control)
        ├─ Franka Hand (gripper interface)
        ├─ ZED SDK (3 cameras)
        └─ ServerInterface (optional: remote NUC)
        ↓
    VRPolicy (Oculus teleoperation)
        ├─ OculusReader (HID input)
        ├─ Pose mapping (VR hand → robot EE)
        └─ Gain tuning (position, rotation, gripper)
        ↓
    DataCollector (trajectory I/O)
        ├─ collect_trajectory() (main loop)
        ├─ HDF5 serialization
        ├─ SVO video recording
        └─ Metadata annotation
        ↓
    Raw Data (trajectory.h5 + .svo files)
        ↓
    Post-Processing (scripts/postprocess.py)
        ├─ SVO → MP4 conversion
        ├─ Validation
        └─ S3 upload (optional)
        ↓
    Training Dataset (pickcup_256_256.h5)
```

---

## Core Classes & Methods

### 1. RobotEnv (robot_env.py)

```python
from droid.robot_env import RobotEnv

# Initialize
env = RobotEnv(
    action_space="cartesian_velocity",  # or joint_position, etc.
    gripper_action_space=None,          # auto-detect
    camera_kwargs={},                   # camera configuration
    do_reset=True
)

# Key Attributes
env.action_space         # "cartesian_velocity" | "joint_position"
env.control_hz           # 15 Hz default
env.reset_joints         # [0, -π/5, 0, -4π/5, 0, 3π/5, 0]
env.camera_reader        # MultiCameraWrapper instance
env.calibration_dict     # Camera extrinsics

# Key Methods
env.step(action)         # Send action to robot, returns action_info
env.reset(randomize=False)  # Move to default pose
env.read_cameras()       # Get camera frames from all 3 ZED cameras
env.get_state()          # Get [state_dict, timestamp_dict]
env.get_camera_extrinsics(state_dict)  # Adjust for gripper camera pose

# State Dict Contents
state_dict = {
    "joint_positions": np.array([...], shape=(7,)),  # rad
    "joint_velocities": np.array([...], shape=(7,)),
    "joint_torques": np.array([...], shape=(7,)),
    "ee_pos": np.array([...], shape=(3,)),           # m in base frame
    "ee_quat": np.array([...], shape=(4,)),          # [qx, qy, qz, qw]
    "gripper_width": float,                          # m
    "gripper_force": float,                          # N
    "image": {
        "cam_id_0": np.array(..., shape=(480, 640, 4)),  # BGRA
        "cam_id_1": np.array(..., shape=(480, 640, 4)),
        "cam_id_2": np.array(..., shape=(480, 640, 4)),
    },
    "camera_extrinsics": {...}
}

# Action Format (cartesian_velocity)
action = np.array([
    vx, vy, vz,           # Linear velocity (m/s)
    wx, wy, wz,           # Angular velocity (rad/s)
    gripper_cmd           # -1 (close) to 1 (open)
])  # Shape: (7,)
```

### 2. VRPolicy (controllers/oculus_controller.py)

```python
from droid.controllers.oculus_controller import VRPolicy

# Initialize
policy = VRPolicy(
    right_controller=True,     # or False for left
    max_lin_vel=1,            # m/s
    max_rot_vel=1,            # rad/s
    max_gripper_vel=1,        # gripper velocity scale
    spatial_coeff=1,          # 3D scaling
    pos_action_gain=5,        # position sensitivity
    rot_action_gain=2,        # rotation sensitivity
    gripper_action_gain=3,    # gripper sensitivity
)

# Key Methods
policy.get_action()    # Read Oculus controller state → robot action
policy.reset_state()   # Reset internal tracking (pose, velocity)
policy.get_info()      # Get user input info (buttons, positions)

# Internal State
policy._state = {
    "poses": {
        "r": [x, y, z, qx, qy, qz, qw],  # Right hand pose (if right_controller=True)
    },
    "trigger": 0 or 1,  # Trigger pressed
    "joystick": [-1, 0, 1],  # Analog joystick axis
}

# Mapping Details
# ─────────────────────────────────────────────────────────
# VR Hand Position (m, relative to global frame)
#   ↓ (minus vr_to_global_mat, global_to_env_mat)
# Cartesian Velocity Command (m/s, in robot base frame)
#
# VR Hand Orientation (quaternion)
#   ↓ (time derivative of orientation)
# Angular Velocity Command (rad/s)
#
# Trigger value ∈ [0, 1]
#   ↓ (normalized to [-1, 1])
# Gripper command
# ─────────────────────────────────────────────────────────
```

### 3. DataCollector (user_interface/data_collector.py)

```python
from droid.user_interface.data_collector import DataCollecter

# Initialize
data_collector = DataCollecter(
    env=env,                           # RobotEnv instance
    controller=policy,                 # VRPolicy instance
    policy=None,                       # Optional policy for autonomous collection
    save_data=True,                    # Save to disk
    save_traj_dir=None,                # Default: droid/data
)

# Key Attributes
data_collector.last_traj_path          # Path to last saved trajectory
data_collector.traj_running            # Currently collecting
data_collector.traj_saved              # Last trajectory success flag
data_collector.success_logdir          # Path to success/ folder
data_collector.failure_logdir          # Path to failure/ folder

# Key Methods
data_collector.collect_trajectory(
    info=None,              # Optional metadata dict
    practice=False,         # Don't save if True
    reset_robot=True        # Reset to default pose first
)
# Saves: data/failure/<timestamp>/trajectory.h5
#        data/failure/<timestamp>/recordings/*.svo

data_collector.change_trajectory_status(success=False)
# Move trajectory to success/ or failure/ folder
# Update trajectory.h5 attrs["success"] and attrs["failure"]

data_collector.calibrate_camera(cam_id, reset_robot=True)
# Interactive camera calibration routine

data_collector.get_camera_feed()
# Return [gui_images_list, camera_ids_list]

data_collector.get_user_feedback()
# Return controller info dict
```

---

## HDF5 File Format

### File Structure (trajectory.h5)

**Location:** `data/success/<YYYY-MM-DD>/<timestamp>/trajectory.h5`

**Contents:**

```
File: trajectory.h5
├── Attributes (metadata)
│   ├── success (bool)
│   ├── failure (bool)
│   ├── time (str) — collection timestamp
│   ├── robot_serial_number (str) — e.g., "FR3-1234"
│   ├── version_number (str) — DROID version
│   ├── user (str) — operator name
│   ├── task_name (str) — task type
│   └── [custom metadata from user]
│
├── dataset: obs (observations at t=0..T)
│   ├── timestamp [T] float64
│   ├── joint_positions [T, 7] float32
│   ├── joint_velocities [T, 7] float32
│   ├── joint_torques [T, 7] float32
│   ├── ee_pos [T, 3] float32
│   ├── ee_quat [T, 4] float32  ← [qx, qy, qz, qw]
│   ├── gripper_width [T, 1] float32
│   ├── gripper_force [T, 1] float32
│   │
│   ├── image (group)
│   │   ├── cam_id_0 [T, 480, 640, 4] uint8  ← BGRA format
│   │   ├── cam_id_1 [T, 480, 640, 4] uint8
│   │   └── cam_id_2 [T, 480, 640, 4] uint8
│   │
│   ├── camera_extrinsics (group)
│   │   ├── cam_id_0 (group)
│   │   │   ├── position [3,] float32  ← relative to base frame
│   │   │   ├── quaternion [4,] float32
│   │   │   ├── matrix [4, 4] float32  ← homogeneous transform
│   │   │   ├── intrinsics [3, 3] float32
│   │   │   └── distortion [5,] float32
│   │   ├── cam_id_1 ...
│   │   └── cam_id_2 ...
│   │
│   └── language (optional, group)
│       ├── task_description (str)
│       └── labels [T] int32  ← phase labels if annotated
│
├── dataset: action [T, 7] float32
│   ├── [0:6] cartesian velocity (vx, vy, vz, wx, wy, wz)
│   └── [6] gripper command ∈ [-1, 1]
│
├── dataset: episode_ends [T] bool
│   └── True at terminal state
│
└── dataset: camera_info (group)
    ├── height 480
    ├── width 640
    ├── num_frames T
    └── frame_rate 15.0 Hz
```

### Reading HDF5 Example

```python
import h5py

with h5py.File("trajectory.h5", "r") as f:
    # Metadata
    print(f"Success: {f.attrs['success']}")
    print(f"Timestamp: {f.attrs['time']}")
    
    # Observations
    T = len(f["obs"]["timestamp"])
    print(f"Trajectory length: {T} frames")
    
    joint_pos = f["obs"]["joint_positions"][:]    # [T, 7]
    ee_pos = f["obs"]["ee_pos"][:]                # [T, 3]
    gripper = f["obs"]["gripper_width"][:]        # [T]
    
    # Images
    cam_0_imgs = f["obs"]["image"]["cam_id_0"][:]  # [T, 480, 640, 4]
    
    # Actions
    actions = f["action"][:]                      # [T, 7]
    
    # Camera extrinsics
    cam_pose = f["obs"]["camera_extrinsics"]["cam_id_0"]["matrix"][:]  # [4, 4]
```

---

## SVO File Format

**Location:** `data/success/<YYYY-MM-DD>/<timestamp>/recordings/*.svo`

**Format:** Binary Stereolabs ZED SDK format

**Characteristics:**
- Stereo video (left + right camera) + depth + metadata
- Compressed (proprietary codec)
- Frame rate: 15 Hz (matched to robot control frequency)
- Resolution: 1280×720 per eye (1920×1080 total)

**Reading SVO (requires ZED SDK):**

```bash
# Convert SVO to MP4 (handled by postprocess.py)
~/zed-sdk-linux/tools/video-to-mp4 recording.svo output.mp4

# Or programmatically
python -c "
import pyzed.sl as sl
cam = sl.Camera()
cam.open()
cam.load(sl.CameraConfiguration(sl.RESOLUTION.HD1080, 15))
while True:
    if cam.grab() == sl.ERROR_CODE.SUCCESS:
        depth = cam.get_measure(sl.MEASURE.DEPTH)
"
```

---

## Training Data HDF5 Format

**Generated by:** `robot_recordings/scripts/build_pickcup_h5.py`

**Structure** (simplified for training):

```
pickcup_256_256.h5
├── demo_0
│   ├── observations
│   │   ├── ee_pos [T, 3]
│   │   ├── ee_quat [T, 4]
│   │   ├── gripper_width [T, 1]
│   │   ├── joint_pos [T, 7]
│   │   ├── images [T, 3, 256, 256, 3]  ← 3 crops/cameras, RGB
│   │   └── timestamps [T]
│   ├── actions
│   │   ├── ee_vel [T, 3]
│   │   ├── ee_rot_vel [T, 3]
│   │   └── gripper_action [T, 1]
│   ├── metadata
│   │   ├── success (bool)
│   │   ├── task (str)
│   │   └── user (str)
│   └── episode_ends [T]
├── demo_1 ...
├── demo_2 ...
└── statistics
    ├── action_mean [7]
    ├── action_std [7]
    ├── image_mean [3, 256, 256, 3]
    └── image_std [3, 256, 256, 3]
```

---

## Processing Pipeline

### Step 1: Raw Collection → trajectory.h5 + .svo

```
RobotEnv.step() → collect_trajectory()
  ├─ Accumulate observations (every 1/15 sec)
  ├─ Accumulate actions from VR controller
  ├─ Record camera frames to .svo (SVO codec)
  └─ Save observations to trajectory.h5
```

### Step 2: Post-Processing (scripts/postprocess.py)

```python
# Validation
- Check HDF5 integrity (all datasets present)
- Verify frame counts match

# SVO → MP4 Conversion
- Extract frames from .svo files
- Re-encode with H.264 (MP4 container)
- Save as recordings/*.mp4

# Metadata Upload
- Upload to S3 bucket (if credentials provided)
- Cache in cache/postprocessing/<lab>-cache.json
```

### Step 3: Training Data Preparation

```python
# build_pickcup_h5.py
for each trajectory.h5:
    → Extract observations + actions
    → Crop images to 256×256
    → Normalize gripper state
    → Compile into single demo entry
    
# Aggregate across all demos
→ Compute normalization statistics
→ Save to pickcup_256_256.h5
```

---

## Camera Calibration

### Calibration Data

**File:** `droid/calibration/calibration_info.json`

```json
{
  "cam_id_0": {
    "intrinsics": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
    "distortion": [k1, k2, p1, p2, k3],
    "extrinsics": {
      "position": [x, y, z],
      "quaternion": [qx, qy, qz, qw],
      "matrix": [[4×4 homogeneous transform]]
    }
  },
  "cam_id_1": {...},
  "cam_id_2": {...}
}
```

### Hand Camera Dynamic Adjustment

```python
# droid/robot_env.py: get_camera_extrinsics()

extrinsics = load_calibration_info()

for cam_id in extrinsics:
    if "hand" in cam_id:  # Hand-mounted camera
        # Adjust for current gripper pose
        gripper_pose = state_dict["ee_pos"], state_dict["ee_quat"]
        extrinsics[cam_id] = adjust_for_gripper_pose(
            extrinsics[cam_id],
            gripper_pose
        )
```

---

## Action Spaces & Control

### Cartesian Velocity (Default)

```python
action = [vx, vy, vz, wx, wy, wz, gripper]
         (m/s)     (rad/s)     (normalized ∈ [-1,1])

# Applied via
env._robot.update_command(
    action,
    action_space="cartesian_velocity",
    blocking=False
)
```

### Joint Velocity

```python
action = [q̇1, q̇2, ..., q̇7, gripper]
         (rad/s × 7)     (normalized)

# Arm joints only (7-DOF)
```

### Cartesian Position

```python
action = [x, y, z, qx, qy, qz, qw, gripper]
         (m × 3)  (quaternion)  (normalized)

# Absolute end-effector pose
```

---

## Troubleshooting & Validation

### Validate HDF5 Integrity

```bash
python << 'EOF'
import h5py
import numpy as np

def validate_trajectory(filepath):
    with h5py.File(filepath, 'r') as f:
        T = len(f["obs"]["timestamp"])
        
        # Check all datasets have same length
        for key in f["obs"].keys():
            if isinstance(f["obs"][key], h5py.Dataset):
                if len(f["obs"][key]) != T:
                    print(f"❌ {key} length mismatch: {len(f['obs'][key])} vs {T}")
                else:
                    print(f"✓ {key}: {f['obs'][key].shape}")
        
        # Check actions
        if "action" in f:
            if len(f["action"]) != T - 1:  # Actions are one frame behind
                print(f"⚠ Action length: {len(f['action'])} (expected {T-1})")
        
        # Check success flag
        print(f"Success: {f.attrs.get('success', 'N/A')}")
        print(f"Frames: {T}")

validate_trajectory("trajectory.h5")
EOF
```

### Check Camera Feed Live

```bash
python << 'EOF'
from droid.robot_env import RobotEnv
env = RobotEnv()

for i in range(10):
    obs, ts = env.get_state()
    print(f"Frame {i}: ee_pos={obs['ee_pos']}, gripper={obs['gripper_width']}")
    print(f"  Cameras: {list(obs['image'].keys())}")
EOF
```

---

## Performance Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Control frequency | 15 Hz | Franka controller limit |
| Observation latency | <100 ms | Camera + state readout |
| Action latency | <50 ms | Command to motor |
| Trajectory length | 20-120 sec | Varies by task |
| Total data rate | ~50-100 MB/min | HDF5 + SVO streams |
| Frames per trajectory | 300-1800 @ 15Hz | 20-120 sec duration |

---

## References & Links

- **DROID Dataset Paper:** https://droid-dataset.github.io/
- **Franka libfranka API:** https://frankaemika.github.io/docs/
- **ZED SDK Documentation:** https://www.stereolabs.com/docs/
- **ROS 2 Humble:** https://docs.ros.org/en/humble/
- **HDF5 Format Spec:** https://www.hdfgroup.org/

