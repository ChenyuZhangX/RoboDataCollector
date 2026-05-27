# Data Collections Project - Robot Infrastructure Survey

**Project Directory:** `/home/robot` on ubuntu server (ssh robot)  
**Working Directory:** `~/projects/data_collections` (local)

---

## Overview

Four interconnected Franka robotics workspaces and data collection systems on the robot server:

1. **franka_ros2_ws** — Official Franka ROS 2 integration (latest framework)
2. **franka_setup** — Duplicate/alternative Franka ROS 2 setup
3. **robot_recordings** — Active data collection and training pipeline (3.7 GB)
4. **mam_franka_ws** — MAM (Mobile Manipulation?) workspace with extended packages

---

## 1. franka_ros2_ws

**Location:** `/home/robot/franka_ros2_ws`  
**Size:** 48 KB (src) + 1.2 GB (build/install)  
**Purpose:** ROS 2 (Humble) middleware for Franka Research 3 robot control

### Structure
```
franka_ros2_ws/
├── src/                    # Source packages (20+ packages)
│   ├── franka_bringup     # Launch robot startup
│   ├── franka_description # URDF models, meshes
│   ├── franka_example_controllers  # Controller implementations
│   ├── franka_gripper     # Franka Hand gripper control
│   ├── franka_semantic_components  # Semantic interface layer
│   ├── integration_launch_testing  # Integration tests
│   └── ... (more packages)
├── build/                 # Compiled objects
├── install/               # Installed binaries & libraries
├── log/                   # Build/runtime logs
├── droid_setup/           # Possibly DROID (diffusion policy) setup
└── Dockerfile, docker-compose.yml  # Container definitions
```

### Key Files
- **src/README.md** — Official documentation (ROS 2 Humble setup guide)
- **src/docker-compose.yml** — Docker environment config
- **.home/** — Custom home directory configuration
- **.openpi-data/** — OpenPI (Open-sourced Procedure Integration?) data cache

### Usage
- **Primary:** ROS 2 control framework for Franka Research 3 arm
- **Setup:** Docker-based (recommended) or local installation with ROS 2 Humble
- **Controllers:** Custom controllers in franka_example_controllers
- **Gripper:** Integrated Franka Hand control via franka_gripper package

### Key Packages (from package.xml inspection)
| Package | Version | Purpose |
|---------|---------|---------|
| franka_semantic_components | 2.1.0 | ROS 2 Control semantic layer |
| franka_gripper | 2.1.0 | Franka Hand gripper interface |
| integration_launch_testing | 2.1.0 | Integration test suite |

---

## 2. franka_setup

**Location:** `/home/robot/franka_setup`  
**Size:** 32 KB (src) + ~1 GB (build/install)  
**Purpose:** Alternate Franka ROS 2 workspace (appears to be a fork/alternative configuration)

### Structure
```
franka_setup/
├── src/                   # Same layout as franka_ros2_ws
│   ├── franka_bringup
│   ├── franka_description
│   ├── franka_example_controllers
│   └── ... (similar packages)
├── build/                 # Compiled artifacts
├── droid_setup/           # DROID-related setup (duplicated)
└── .openpi-data/          # OpenPI cache
```

### Differences from franka_ros2_ws
- Last modified 2025-05-14 (more recent than franka_ros2_ws: 2025-05-10)
- Slightly different .openpi-data structure
- Likely a configuration variant or backup

### Usage
- **Secondary workspace** for testing alternative configurations
- May be used for A/B testing different control stacks
- Could be for different hardware setup or experimental features

---

## 3. robot_recordings

**Location:** `/home/robot/hebu/robot_recordings`  
**Size:** 3.7 GB  
**Purpose:** Active robot data collection and manipulation learning dataset

### Structure
```
robot_recordings/
├── at/                    # Pick-cup assembly task trajectories
│   ├── traj_*/            # 117 trajectory directories (113 with valid data)
│   │   └── replay/
│   │       └── joint_trajectory.npz  # Recorded joint states + timestamps
│   └── at_damaged/        # Corrupted/failed trajectories (95 MB)
│
├── Data files (1.6-1.6 GB each)
│   ├── pickcup_crop.h5    # Cropped camera image dataset
│   ├── pickcup_256_256.h5 # 256×256 resolution dataset
│   └── pickcup_20hz_new.h5 # 20 Hz downsampled dataset (586 MB)
│
├── scripts/               # Data processing utilities
│   ├── build_pickcup_h5.py        # Convert NPZ → HDF5
│   ├── downsample_h5_20hz.py      # Temporal downsampling
│   ├── convert_pickcup_20hz_to_euler_gripper.py  # Format conversion
│   └── extract_one_demo_h5.py     # Extract single demo
│
├── franka_train/          # Training code directory (148 KB)
├── runs/                  # Experiment results & logs (13 GB)
├── logs/                  # Processing logs (376 KB)
├── examples/              # Example scripts (8 KB)
├── test_crop/             # Test dataset variants (20 MB)
├── data_process.md        # Data processing documentation
└── .deps/                 # Dependencies (numpy, etc.)
```

### Data Statistics (from data_process.md)
| Metric | Value |
|--------|-------|
| Total trajectories | 117 |
| Valid demos (with replay data) | 113 |
| Total timesteps | 161,849 |
| Min demo length | 859 steps |
| Max demo length | 2,766 steps |
| Median | 1,293 steps |
| Mean | 1,432 steps |

**Length distribution:**
- <1000: 9 demos
- 1000-1199: 27 demos
- 1200-1399: 34 demos
- 1400-1599: 16 demos
- 1600-1999: 14 demos
- ≥2000: 13 demos

**Missing data:** traj_28, traj_31, traj_39, traj_133 (no replay/joint_trajectory.npz)

### Key Scripts

**build_pickcup_h5.py** — Main data pipeline
- Reads all `traj_*/replay/joint_trajectory.npz` files
- Combines into single HDF5 dataset
- Likely includes camera images and robot state

**convert_pickcup_20hz_to_euler_gripper.py**
- Converts quaternion → Euler angles (gripper representation)
- Standardizes data format for training

**downsample_h5_20hz.py**
- Reduces temporal resolution to 20 Hz
- Creates pickcup_20hz_new.h5 from higher-frequency data

### Usage
- **Primary:** Training dataset for pick-and-place / assembly tasks
- **Task:** "pick-cup" manipulation task (repeated 113 times)
- **Modality:** Joint trajectories (7-DOF Franka arm) + gripper state + camera images
- **Format:** HDF5 (h5) and NPZ with timestamps

---

## 4. mam_franka_ws

**Location:** `/home/robot/hebu/mam_franka_ws`  
**Size:** 24 KB (wrapper) + unknown inner size  
**Purpose:** Extended Franka workspace with semantic components and gripper calibration

### Structure
```
mam_franka_ws/
└── mam_franka_ws/         # Inner workspace (nested structure)
    ├── franka_semantic_components/  # Semantic layer
    │   ├── src/
    │   ├── include/
    │   ├── doc/
    │   └── test/
    │
    ├── franka_gripper/     # Gripper control package
    │   ├── franka_gripper/  # Main gripper node
    │   ├── scripts/        # Helper scripts
    │   ├── launch/         # Launch files
    │   ├── config/         # Configuration files
    │   └── doc/
    │
    ├── calibrate_cameras.py # Camera calibration utility
    ├── calibration/        # Camera calibration data
    ├── integration_launch_testing/
    ├── docs/               # Documentation (with assets/)
    │
    └── Docker files        # Container definitions
```

### Key Features
- **calibrate_cameras.py** — Camera extrinsic calibration script
- **franka_gripper scripts/** — Likely contains:
  - Gripper force/torque estimation
  - Motion analysis utilities
  - State detection scripts
- **Semantic components** — Higher-level abstraction over low-level control

### Usage
- **Secondary:** Extends franka_ros2_ws with semantic layers
- **Calibration:** Camera extrinsic calibration for visual servoing
- **Gripper:** Enhanced gripper control (MAM = Mobile-Arm Manipulation?)
- **Integration:** Bridges between visual perception and robotic control

---

## 5. droid_setup (Present in Multiple Workspaces)

**Locations:** 
- `/home/robot/franka_ros2_ws/droid_setup`
- `/home/robot/franka_setup/droid_setup`

**Purpose:** Integration with DROID (Diffusion Policy-based Robot Learning?)

**Contents:**
- Likely contains:
  - Diffusion policy implementations
  - Vision transformer modules
  - Policy training utilities
  - DROID-specific launch configurations

**Status:** Experimental feature present in both main workspaces

---

## Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ ROS 2 Control Stack (franka_ros2_ws, franka_setup)         │
│ └─ Franka arm control @ 1 kHz via libfranka               │
│ └─ Gripper control (Franka Hand)                          │
│ └─ Joint trajectory execution                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
        ┌──────────────────────────────────────┐
        │ Data Collection Layer                 │
        │ (robot_recordings/at/traj_*/)        │
        │ └─ 113 pick-cup trajectories         │
        │ └─ Joint states + timestamps         │
        │ └─ Camera images (calibrated)        │
        └──────────────────────────────────────┘
                           ↓
        ┌──────────────────────────────────────┐
        │ Data Processing (scripts/)            │
        │ └─ NPZ → HDF5 conversion             │
        │ └─ 20 Hz downsampling                │
        │ └─ Quaternion → Euler conversion     │
        └──────────────────────────────────────┘
                           ↓
        ┌──────────────────────────────────────┐
        │ Training Dataset (robot_recordings)  │
        │ ├─ pickcup_crop.h5 (1.6 GB)        │
        │ ├─ pickcup_256_256.h5 (1.6 GB)     │
        │ └─ pickcup_20hz_new.h5 (586 MB)    │
        └──────────────────────────────────────┘
                           ↓
        ┌──────────────────────────────────────┐
        │ DROID / Policy Learning              │
        │ (franka_*/droid_setup/)              │
        │ └─ Diffusion policy training         │
        │ └─ Experiment results (runs/)        │
        └──────────────────────────────────────┘
```

---

## Key Observations

1. **Dual Control Stacks:**
   - `franka_ros2_ws` and `franka_setup` are nearly identical → likely for redundancy or A/B testing
   - Both use ROS 2 Humble with Franka 2.1.0 packages

2. **Active Dataset:**
   - `robot_recordings` is the main work-in-progress
   - 113 valid pick-cup trajectories, 161k+ total timesteps
   - Data is being processed into multiple HDF5 formats for training

3. **Modular Architecture:**
   - `mam_franka_ws` extends base control with semantic layers and calibration
   - Suggests integration of vision + manipulation

4. **DROID Integration:**
   - Diffusion policy framework present in both workspaces
   - 13 GB of experiment results → active training/experimentation

5. **Data Pipeline Maturity:**
   - Automated scripts for format conversion and downsampling
   - Multiple dataset variants (crop, 256×256, 20 Hz) suggest different use cases
   - Well-documented data statistics in `data_process.md`

---

## Working with These Systems

### Common Operations

**Build & Test Control Stack:**
```bash
ssh robot
cd ~/franka_ros2_ws
colcon build --packages-select franka_gripper
source install/setup.bash
ros2 launch franka_bringup franka.launch.py
```

**Inspect Data:**
```bash
ssh robot
cd ~/hebu/robot_recordings
python3 scripts/extract_one_demo_h5.py pickcup_crop.h5 0  # Extract demo 0
```

**Process New Trajectories:**
```bash
# After recording new traj_* folders in at/
python3 scripts/build_pickcup_h5.py --output new_dataset.h5
```

**Training Experiments:**
```bash
# Results logged in runs/
# Check experiment logs and metrics
ls -lh runs/ | tail -20
```

---

## Dependencies & Environment

- **ROS 2:** Humble (Ubuntu 22.04)
- **libfranka:** Latest (via ROS packages)
- **Python:** 3.9+ (for data processing)
- **HDF5:** libhdf5 (for dataset I/O)
- **Vision:** Camera calibration tools (likely OpenCV)
- **ML:** PyTorch / JAX (for DROID training, not explicitly visible)

---

## Data Collection Pipeline (DROID)

### How Data is Collected

**Entry Point:** `droid_setup/droid/scripts/main.py`

**Three-Component System:**

1. **RobotEnv** (`robot_env.py`)
   - Gym-compatible environment wrapper
   - Supports multiple action spaces: cartesian_position, cartesian_velocity, joint_position, joint_velocity
   - Multi-camera reader with calibration
   - 15 Hz control frequency
   - Direct libfranka access or ServerInterface (remote NUC control)

2. **VRPolicy (Oculus Controller)** (`controllers/oculus_controller.py`)
   - Real-time teleoperation via Meta Oculus VR headset
   - Maps VR hand pose → robot gripper cartesian velocity
   - Supports left/right controller configuration
   - Configurable gains for position, rotation, gripper

3. **DataCollector** (`user_interface/data_collector.py`)
   - GUI integration point
   - Manages trajectory collection workflow
   - Saves trajectories to `success/` or `failure/` folders
   - Stores metadata: timestamp, robot info, version, user
   - Handles camera calibration
   - Renames trajectories based on success label post-collection

**Collection Data Format:**

```
data/
├── success/
│   └── <YYYY-MM-DD>/
│       └── <timestamp>/
│           ├── trajectory.h5          # Main data file (observations + metadata)
│           └── recordings/
│               ├── <cam_id_0>.svo     # ZED stereo video (binary format)
│               ├── <cam_id_1>.svo
│               └── <cam_id_2>.svo
└── failure/
    └── <YYYY-MM-DD>/
        └── <timestamp>/
            └── ... (same structure, marked as failure)
```

### Launch Data Collection

**Quick Start:**
```bash
ssh robot
cd ~/franka_ros2_ws/droid_setup/droid

# Right controller (default)
python scripts/main.py

# Or left controller
python scripts/main.py --left_controller
```

**What Happens:**
1. GUI boots (Tkinter interface with live camera feeds)
2. User logs in → selects task → configures scene
3. Robot resets to neutral pose
4. User teleoperates via Oculus headset
5. On button press, trajectory is collected and saved
6. User labels as success/failure
7. Trajectory moved to appropriate folder

### Storage & Formats

**Raw Collection Files:**
- **trajectory.h5** — HDF5 file containing:
  - Robot joint states (7-DOF)
  - End-effector pose (position + quaternion)
  - Gripper width/force
  - Camera intrinsics/extrinsics (for each camera)
  - Metadata (task, user, timestamp, success flag)
  - **No camera images stored here** (too large)

- **.svo files** — Stereo video format
  - Binary format from ZED SDK
  - Contains both left + right camera frames + depth
  - 3 cameras → 3 .svo files per trajectory

**Post-Processing** (`scripts/postprocess.py`):
- Converts .svo → .mp4 (compresses video)
- Validates trajectory completeness
- Uploads to AWS S3 bucket (lab-specific credentials)
- Manages cache to avoid duplicate uploads

### Data Processing to HDF5

**Pipeline in robot_recordings/scripts/:**

```bash
# 1. Build combined HDF5 dataset from NPZ files
python scripts/build_pickcup_h5.py \
  --input_dir ~/hebu/robot_recordings/at \
  --output_h5 pickcup_full.h5

# 2. Convert quaternion → Euler + fix gripper format
python scripts/convert_pickcup_20hz_to_euler_gripper.py \
  --input_h5 pickcup_full.h5 \
  --output_h5 pickcup_20hz_euler.h5

# 3. Downsample to 20 Hz (from higher freq)
python scripts/downsample_h5_20hz.py \
  --input_h5 pickcup_20hz_euler.h5 \
  --output_h5 pickcup_20hz_downsampled.h5

# 4. Extract crops for training
python scripts/extract_one_demo_h5.py \
  pickcup_20hz_downsampled.h5 <demo_idx>
```

**HDF5 Dataset Structure** (approximate):
```
pickcup_256_256.h5
├── demo_0/
│   ├── observations/
│   │   ├── ee_pos            [T, 3]      # End-effector XYZ
│   │   ├── ee_quat           [T, 4]      # Quaternion
│   │   ├── gripper_width     [T, 1]
│   │   ├── joint_pos         [T, 7]
│   │   ├── joint_vel         [T, 7]
│   │   └── images            [T, 3, 256, 256, 3]  # 3 cameras
│   ├── actions/
│   │   ├── ee_vel            [T, 3]      # Cartesian velocity commands
│   │   ├── ee_rot_vel        [T, 3]      # Rotation velocity
│   │   └── gripper_action    [T, 1]
│   ├── metadata/
│   │   ├── timestamps        [T]
│   │   ├── success           bool
│   │   └── task_name         str
│   └── episode_ends          [T]
├── demo_1/
│   └── ...
└── attributes:
    ├── num_demos
    ├── compression
    └── collection_date
```

---

## Collection Workflow Summary

### Step 1: Start Collection GUI
```bash
ssh robot
cd ~/franka_ros2_ws/droid_setup/droid
python scripts/main.py --right_controller
```

### Step 2: Login & Configure
- **Login Page:** User name (for metadata)
- **Task Selection:** Choose task type (e.g., "pick-cup")
- **Scene Config:** Configure workspace (lighting, object positions)
- **Camera Check:** Verify all 3 cameras are live

### Step 3: Teleoperate
- **VR Headset:** User puts on Oculus
- **Oculus Controller:** Maps to robot
  - Thumb joystick → gripper open/close
  - Hand position → EE cartesian velocity
  - Trigger → record trajectory start/stop
- **Live Feedback:** See camera feeds in GUI + VR

### Step 4: Save & Label
- Trajectory saved with timestamp
- User immediately labels: **Success** or **Failure**
- File moves to `data/success/` or `data/failure/`
- HDF5 + .svo files stored

### Step 5: Post-Process
```bash
# Convert SVO videos to MP4
python scripts/postprocess.py

# Upload to S3 (requires AWS credentials)
# Results cached in cache/postprocessing/<lab>-cache.json
```

### Step 6: Training Data Pipeline
```bash
cd ~/hebu/robot_recordings

# Convert raw trajectories to consolidated HDF5
python scripts/build_pickcup_h5.py --input_dir at/

# Format standardization
python scripts/convert_pickcup_20hz_to_euler_gripper.py

# Downsample for faster training
python scripts/downsample_h5_20hz.py
```

---

## Key Files to Understand

| File | Purpose |
|------|---------|
| `droid/scripts/main.py` | Collection entry point (Oculus + GUI) |
| `droid/robot_env.py` | ROS 2 ↔ robot interface wrapper |
| `droid/controllers/oculus_controller.py` | VR hand → robot mapping |
| `droid/user_interface/data_collector.py` | Trajectory I/O & HDF5 saving |
| `droid/user_interface/gui.py` | Tkinter GUI (1500×1200) |
| `robot_recordings/scripts/build_pickcup_h5.py` | Raw → training dataset |
| `robot_recordings/data_process.md` | Data statistics & collection notes |

---

## Common Issues & Troubleshooting

**Issue:** Oculus controller not detected
- Solution: Check USB connection on data collection laptop
- Restart GUI: `Ctrl+C`, rerun `python scripts/main.py`

**Issue:** Cameras showing black frames
- Solution: Check camera USB connections (3 ZED cameras)
- Recalibrate: Use GUI "Calibration" tab

**Issue:** HDF5 files corrupted (can't read)
- Solution: Incomplete trajectory (early disconnect)
- Check logs in `robot_recordings/logs/`

**Issue:** SVO files too large
- Solution: Use downsampling or video compression
- `scripts/postprocess.py` converts to MP4 (lossy)

---

## Next Steps for Your Data Collection Work

1. **First Collection Session:**
   - Reserve 1-2 hours with Oculus headset
   - Collect 5-10 practice trajectories (learn VR control)
   - Verify data structure in `data/success/` folder

2. **Extend robot_recordings dataset:**
   - Link new collections to `~/hebu/robot_recordings/at/traj_N/`
   - Run `build_pickcup_h5.py` to merge with existing data
   - Update `data_process.md` with new statistics

3. **Validate Data Quality:**
   - Check HDF5 structure with `h5dump` command
   - Verify all 113 trajectories load correctly
   - Spot-check 10 random trajectories for artifacts

4. **Setup Training Pipeline:**
   - Install diffusion policy: `pip install diffusion_policy`
   - Configure `robot_recordings/franka_train/` scripts
   - Start baseline training on `pickcup_256_256.h5`

5. **Monitor Experiments:**
   - Results logged in `robot_recordings/runs/<exp_name>/`
   - Tensorboard: `tensorboard --logdir runs/`
   - Track convergence, loss curves, policy validation

---

**Last Updated:** 2026-05-21  
**Created by:** Codebase Survey
