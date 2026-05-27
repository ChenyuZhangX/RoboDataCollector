# DROID Data Collection - Quick Start Guide

**Last Updated:** 2026-05-21  
**Target:** First-time data collection with Franka Research 3 + Oculus VR headset

---

## Prerequisites Checklist

Before collecting data, verify:

- [ ] Franka Research 3 arm is powered on and connected
- [ ] All 3 ZED Mini cameras are connected via USB
- [ ] Oculus Meta Quest 2/3 headset is charged and paired
- [ ] NUC or data collection laptop is running Ubuntu 22.04
- [ ] ROS 2 Humble is installed: `echo $ROS_DISTRO` → "humble"
- [ ] DROID code is cloned: `ls ~/franka_ros2_ws/droid_setup/droid`
- [ ] Data directory exists: `mkdir -p ~/franka_ros2_ws/droid_setup/droid/data`

---

## Pre-Collection Setup (10 minutes)

### 1. SSH into Robot Server

```bash
ssh robot  # Connects to data collection laptop
```

### 2. Source ROS 2 Environment

```bash
source /opt/ros/humble/setup.bash
# Verify
ros2 node list  # Should show some nodes
```

### 3. Navigate to DROID Collection

```bash
cd ~/franka_ros2_ws/droid_setup/droid
```

### 4. Verify System Ready

```bash
# Check robot connection
python -c "from franka.robot import FrankaRobot; r = FrankaRobot(); print(f'Robot ready: {r.get_robot_state()}')"

# Check cameras
python -c "from droid.camera_utils.info import camera_type_dict; print(camera_type_dict)"

# Check Oculus
python -c "from oculus_reader.reader import OculusReader; o = OculusReader(); print('Oculus OK')"
```

If all pass → proceed to collection.

---

## Launching Collection (5 minutes)

### Step 1: Start the GUI

```bash
python scripts/main.py --right_controller
```

**Expected Output:**
```
[INFO] Initializing RobotEnv...
[INFO] Connecting to Franka robot...
[INFO] Loading cameras: cam_id_0, cam_id_1, cam_id_2
[INFO] Initializing VR controller (right)...
[INFO] GUI starting on port 1500x1200...
```

**GUI Should Appear:** Tkinter window with:
- Left: Login form
- Center: Live camera feeds (3 rectangles, showing real-time images)
- Right: Control buttons

### Step 2: Login

1. Enter your name in the text field
2. Press "Enter" or click "Login"
3. → Redirects to "Robot Reset" page

### Step 3: Robot Reset

The robot will:
1. Move gripper to neutral (open)
2. Move joints to default pose: `[0, -π/5, 0, -4π/5, 0, 3π/5, 0]`
3. Status light on arm base turns **blue** → ready

Wait ~10 seconds for this to complete.

---

## Your First Collection (2-5 minutes per trajectory)

### Pre-Collection Checklist

- [ ] VR headset on your head
- [ ] Right Oculus controller in your right hand
- [ ] All cameras showing live frames (not black)
- [ ] Robot is at reset position (check joint angles on screen)

### Collection Steps

1. **Scene Configuration Page**
   - Select task: e.g., "pick_cup" (or leave empty if none defined)
   - Click "Continue" → moves to camera verification

2. **Camera Page**
   - You'll see 3 live camera feeds (thumbnail + enlarged)
   - Click any camera to enlarge it
   - Verify no camera is showing all-black frames
   - If black: USB disconnected, reconnect and restart GUI
   - Click "Continue" → ready to collect

3. **Wearing VR Headset**
   - Put on Oculus Meta Quest (right controllers enabled)
   - Look around the scene (3 cameras should match what you see)
   - Do a test motion: Move your hand forward → robot gripper should move toward table

4. **Teleoperation**
   - **Hand Position:** Your hand's 3D position → Robot's end-effector cartesian velocity
     - Move hand left ↔ gripper moves left
     - Move hand up ↓ gripper moves down
     - Move hand forward → gripper moves forward (into workspace)
   
   - **Thumb Joystick:** Gripper opening/closing
     - Push joystick UP → gripper opens
     - Push joystick DOWN → gripper closes
   
   - **Trigger Button:** Start/stop recording
     - Hold **trigger to record trajectory**
     - Release trigger to stop (trajectory saved automatically)
     - **Total trajectory length:** Usually 20-60 seconds per manipulation task

5. **Example Pick-Up Motion**
   ```
   1. Move hand near target object (gripper approaches)
      [~5 seconds]
   2. Close gripper (squeeze joystick down)
      [~2 seconds]
   3. Lift hand upward
      [~3 seconds]
   4. Move to drop location
      [~5 seconds]
   5. Open gripper (push joystick up)
      [~2 seconds]
   6. Move away
      [~3 seconds]
   Total: ~20 seconds
   ```

### After Collection

6. **Success/Failure Label**
   - Did the task succeed? (e.g., cup picked up and placed)
   - Click "SUCCESS" → trajectory saved to `data/success/`
   - Click "FAILURE" → trajectory saved to `data/failure/`
   - Either way, data is retained for later use

7. **Next Trajectory**
   - Robot resets to default pose
   - GUI returns to scene config
   - Repeat from Step 1 for next trajectory

---

## Data Saved

After each collection, a folder is created:

```
~/franka_ros2_ws/droid_setup/droid/data/
└── success/
    └── 2026-05-21/
        └── Wed_May_21_14_32_45_2026/
            ├── trajectory.h5          # ~50-200 MB (robot states + metadata)
            └── recordings/
                ├── cam_id_0.svo       # ~50-100 MB (ZED left+right stereo)
                ├── cam_id_1.svo
                └── cam_id_2.svo
```

**Total per trajectory:** ~500 MB - 1 GB

---

## Troubleshooting During Collection

### Problem: Oculus controller not responding
**Symptom:** VR headset shows home screen, hand controller not moving gripper  
**Fix:**
1. Check USB connection on PC (should see `/dev/ttyUSB*`)
2. Restart GUI: `Ctrl+C`, then `python scripts/main.py`
3. If USB unplugged mid-collection, force-close script and rerun

### Problem: Camera shows black frames
**Symptom:** Live feed is all black or frozen  
**Fix:**
1. Check USB connections for all 3 ZED cameras (use `lsusb` to verify)
2. Physically reconnect cameras
3. Restart GUI
4. If persists, run camera test: `python -c "from droid.camera_utils.multi_camera_reader import MultiCameraReader; m = MultiCameraReader(); print(m.read())"`

### Problem: Robot doesn't move when I move my hand
**Symptom:** GUI running, VR on, but no robot motion  
**Fix:**
1. Check robot connection: `ros2 node list` should show `/franka_control`
2. Is the External Enabling Device pressed? (Red button on lab bench)
   - Must be held down to enable motion
   - Release to emergency stop
3. Check if any joints are in error state (arm light red/orange)
4. Restart collection: Exit GUI, run `python scripts/main.py` again

### Problem: GUI window is too small or unreadable
**Symptom:** Text or buttons cut off  
**Fix:**
```bash
# Edit gui.py to change window size
nano ~/franka_ros2_ws/droid_setup/droid/droid/user_interface/gui.py
# Change: self.geometry("1500x1200")  →  self.geometry("1920x1440")
# Restart GUI
```

---

## After First Collection Session

### 1. Verify Data Saved

```bash
ls -lah ~/franka_ros2_ws/droid_setup/droid/data/success/*/

# Should show:
# drwxrwxr-x ... Wed_May_21_14_32_45_2026
# Inside: trajectory.h5 + recordings/ folder
```

### 2. Inspect HDF5 File

```bash
pip install h5py
python << 'EOF'
import h5py

h5_file = "~/franka_ros2_ws/droid_setup/droid/data/success/2026-05-21/*/trajectory.h5"
# Expand * to actual directory

with h5py.File(h5_file, 'r') as f:
    print("Keys:", list(f.keys()))
    print("Metadata:", dict(f.attrs))
    if 'obs' in f:
        print("Observations:", dict(f['obs'].keys()))
        print("  Timestamp shape:", f['obs']['timestamp'].shape)
        print("  Joint position shape:", f['obs']['joint_positions'].shape)
EOF
```

### 3. Convert for Training

After collecting 10-50 trajectories:

```bash
cd ~/hebu/robot_recordings

# Aggregate all your new data
python scripts/build_pickcup_h5.py \
  --input_dir ~/franka_ros2_ws/droid_setup/droid/data/success \
  --output_h5 my_collected_data.h5

# Validate
python scripts/extract_one_demo_h5.py my_collected_data.h5 0
```

---

## Collection Tips & Best Practices

### Comfortable Teleoperation

1. **Calibrate Hand Position**
   - At start of each session, do 2-3 practice motions
   - Get feel for hand → end-effector mapping
   - Gains are configurable in `oculus_controller.py` if too sensitive

2. **Smooth Motions**
   - Slow, deliberate movements → better data quality
   - Jerky motions cause poor trajectories
   - Imagine you're controlling a delicate robot (you are!)

3. **Gripper Sensitivity**
   - Joystick axis: 0 (neutral) → 1 (fully open) → -1 (fully closed)
   - Small movements = fine control
   - Practice before real collection

### Data Quality

4. **Check Replay**
   - After 5-10 trajectories, watch replay to verify quality
   - Look for: smooth motion, proper gripper behavior, no collisions
   - If bad, note what went wrong in `data_process.md`

5. **Consistent Task**
   - Collect 20-30 demonstrations of same task
   - Vary object positions slightly for diversity
   - Keep scene setup consistent

6. **Label Accurately**
   - SUCCESS = task fully completed
   - FAILURE = partial, collision, gripper dropped object, etc.
   - Accurate labels improve downstream training

### Performance

7. **Storage**
   - Each trajectory: ~500 MB - 1 GB
   - Plan for 50-100 GB if collecting 50-100 trajectories
   - External SSD recommended for large collections

8. **Backup**
   - After 20-30 successful collections, copy to backup:
     ```bash
     rsync -av ~/franka_ros2_ws/droid_setup/droid/data/ /backup/robot_data/
     ```

---

## Next: Post-Processing & Training

Once you've collected 20+ trajectories:

```bash
# 1. Post-process (convert SVO → MP4, upload metadata)
cd ~/franka_ros2_ws/droid_setup/droid
python scripts/postprocess.py

# 2. Merge into robot_recordings dataset
cd ~/hebu/robot_recordings
python scripts/build_pickcup_h5.py

# 3. Start training (see franka_train/ for details)
python franka_train/train_baseline_franka.py \
  --data_h5 pickcup_256_256.h5 \
  --output_dir runs/my_experiment
```

---

## Reference: Oculus Controls Summary

| Control | Action |
|---------|--------|
| **Hand Position** | End-effector cartesian velocity (3D motion) |
| **Thumb Joystick ↑** | Open gripper |
| **Thumb Joystick ↓** | Close gripper |
| **Trigger** | Record trajectory (hold) |
| **A/B Buttons** | GUI navigation (if needed) |
| **Menu Button** | Pause/exit GUI |

---

## Emergency Stop

If anything goes wrong:

1. **Immediate:** Release Oculus trigger (stops trajectory recording)
2. **Quick:** Release joystick / hand motion
3. **Emergency:** Press **red button on lab bench** (External Enabling Device)
   - Robot enters emergency stop mode
   - All motion halted immediately
   - Arm light turns **red**
4. **Recovery:** Press reset button on arm (blue button), restart GUI

---

## Support

If stuck:

- Check logs: `tail -n 50 ~/franka_ros2_ws/droid_setup/droid/logs/*.log`
- Read DROID docs: `~/franka_ros2_ws/droid_setup/droid/scripts/README.md`
- Check repo issues: https://github.com/droid-dataset/droid (upstream)
- Review data_process.md in robot_recordings for prior issues

**Happy collecting!** 🚀
