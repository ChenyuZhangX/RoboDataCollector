# Data Collection — 操作指南

**硬件配置：**
- Franka Research 3 机械臂
- Robotiq 2F-85 夹爪（USB-RS485 串口）
- ZED-M 腕部相机（USB3，V4L2 直接读取）
- RealSense D435 第三视角相机（ROS 2 topic）

**工作目录：** `~/chenyu/data_collection/`

---

## 目录结构

```
~/chenyu/data_collection/
├── scripts/
│   ├── find_zed_device.sh             Bash：自动检测 ZED-M 设备节点
│   ├── find_zed_device.py             Python：自动检测 ZED-M 设备节点
│   ├── collect_zed_mono_images.py     单独采图（不依赖 ROS2）
│   └── record_zed_mono_video.py       单独录视频（不依赖 ROS2）
├── ros2_ws/
│   └── src/
│       └── zed_mono_v4l2/             ROS2 包：发布 ZED-M 单目 topic
├── teach_collect/
│   └── teach_replay_robotiq.py        主采集脚本（手拖 EEF）
├── data/                              采集数据存储根目录
│   └── <folder_name>/
│       ├── traj_0/
│       │   ├── teach/
│       │   │   ├── joint_trajectory.npz
│       │   │   ├── gripper_events.npz
│       │   │   ├── wrist_zed.avi
│       │   │   └── third_rs.avi
│       │   └── replay/
│       │       ├── joint_trajectory.npz
│       │       ├── joint_velocities.npz
│       │       ├── end_effector_pose.npz
│       │       ├── gripper_events.npz
│       │       ├── wrist_zed.avi
│       │       └── third_rs.avi
│       └── traj_1/ ...
└── README.md
```

---

## 快速开始（完整流程）

### 步骤 1：检查所有硬件连接

```bash
# 检查 ZED-M
lsusb | grep -i -E "zed|stereo|2b03"
# 必须看到 2b03:f682 (video interface) + 2b03:f681 (HID)
v4l2-ctl --list-devices   # 确认 /dev/videoX 存在

# 检查 Robotiq 串口
ls /dev/ttyUSB*
# 应该看到 /dev/ttyUSB0 或类似

# 检查 RealSense（通过 ROS2 topic）
# 稍后在所有节点启动后执行
ros2 topic list | grep camera
```

---

### 步骤 2：启动 Robotiq 夹爪驱动

新开终端：

```bash
cd ~/chenyu/robotiq_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch robotiq_description robotiq_control.launch.py \
  com_port:=/dev/ttyUSB0 \
  launch_rviz:=false
```

等待日志出现：
```
Robotiq Gripper successfully activated!
Successful 'activate' of hardware 'RobotiqGripperHardwareInterface'
```

> 保持此终端运行，不要关闭。

---

### 步骤 3：启动 Franka ROS2 控制栈（teach_replay 模式）

新开终端：

```bash
cd ~/franka_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch franka_bringup teach_replay.launch.py
```

等待日志稳定，无报错。

> 保持此终端运行。

---

### 步骤 4：启动 RealSense 相机（如果未自动启动）

新开终端：

```bash
# 方式 A：使用 realsense2_camera 包
source /opt/ros/humble/setup.bash
ros2 launch realsense2_camera rs_launch.py

# 方式 B：如果已经在 mam_franka_ws 里启动，确认 topic 存在
ros2 topic list | grep /camera/color
ros2 topic hz /camera/color/image_raw  # 应显示约 30 Hz
```

---

### 步骤 5：启动主采集脚本

新开终端：

```bash
cd ~/chenyu/data_collection
source /opt/ros/humble/setup.bash
source ~/franka_ros2_ws/install/setup.bash
# 如果 Robotiq 在单独 ws
source ~/chenyu/robotiq_ws/install/setup.bash

python3 teach_collect/teach_replay_robotiq.py \
  --output_dir ~/chenyu/data_collection/data \
  --fps 30 \
  --record_rate 100 \
  --realsense_topic /camera/color/image_raw
```

**启动时会提示输入文件夹名：**
```
Enter save folder name: pick_cup_session1
```

脚本会输出：
```
[INFO] ZED-M auto-detected: /dev/video4
[INFO] ZED-M wrist camera started.
[INFO] RealSense topic: /camera/color/image_raw
[INFO] Robotiq gripper client ready
[INFO] ============================
[INFO] Teach-Replay Robotiq — Keys:
[INFO]   t : start teaching
[INFO]   o : gripper OPEN
[INFO]   c : gripper CLOSE
[INFO]   s : stop + save
[INFO]   r : replay
[INFO]   after replay → 1=save  2=discard  3=replay-again
[INFO]   h : gripper home
[INFO]   q : quit
[INFO] ============================
```

---

## 采集一条轨迹（完整操作流程）

### 1. 开始采集（按 t）

```
[按 t]
```

机械臂进入 **零力矩模式（TEACH mode）**，此时：
- 机械臂重力已补偿，可以轻松用手拖动
- ZED-M 和 RealSense 同时开始录像（保存到 `teach/` 文件夹）
- 关节位置以 100 Hz 采样

> ⚠️ 注意：需要踩下**外部使能装置**（脚踏板）才能允许机械臂被动运动。

### 2. 手动拖动机械臂

用手轻轻推动机械臂末端（EEF）：

```
推动到物体上方 → [按 c 关闭夹爪] → 抬起 → 移到放置位 → [按 o 打开夹爪] → 撤回
```

**夹爪控制：**
| 按键 | 动作 | Robotiq 位置 |
|------|------|-------------|
| **o** | 打开夹爪 | 0.000 m（完全张开）|
| **c** | 关闭夹爪 | 0.085 m（完全闭合）|

**注意事项：**
- 动作要平稳，避免突然加速
- 每个关键姿态停顿 0.5-1 秒
- 整条轨迹通常 15-60 秒

### 3. 保存教学轨迹（按 s）

```
[按 s]
```

输出：
```
[INFO] Teaching saved (850 samples). Press 'r' to replay.
```

保存文件：
```
traj_0/teach/
├── joint_trajectory.npz   关节位置 [T, 7] + 时间戳 [T] + 夹爪指令 [T]
├── gripper_events.npz      夹爪事件 (相对时刻, 动作)
├── wrist_zed.avi           ZED-M 腕部相机录像
└── third_rs.avi            RealSense 第三视角录像
```

### 4. 回放验证（按 r）

```
[按 r]
```

机械臂**自动执行**刚才教学的轨迹：
- 两台相机同时录像到 `replay/` 目录
- 关节实际执行位置以 100 Hz 记录
- 末端执行器姿态同步记录
- 夹爪事件按教学时刻自动执行

观察机械臂执行是否符合预期。

### 5. 保存或丢弃回放

```
[按 1 或 s]  → 保存此次回放，准备下一条轨迹
[按 2 或 d]  → 丢弃回放，保留教学数据，再按 r 可重新回放
[按 3 或 r]  → 重新回放（覆盖之前的回放记录）
```

选 1（保存）后输出：
```
[INFO] Saved: /home/robot/chenyu/data_collection/data/pick_cup_session1/traj_0
[INFO] Ready for next trajectory. Press 't' to teach.
```

### 6. 重复采集下一条

回到步骤 1，继续按 t 开始下一条轨迹（自动编号 traj_1, traj_2, ...）。

---

## 完整保存数据格式

```
data/<session_name>/traj_N/
├── teach/
│   ├── joint_trajectory.npz
│   │   ├── timestamps        [T]       相对时刻（秒）
│   │   ├── joint_positions   [T, 7]    关节角（弧度）
│   │   └── gripper_cmd       [T]       夹爪指令（0.0=开, 0.085=闭）
│   ├── gripper_events.npz
│   │   ├── relative_times    [N]       相对时刻（秒）
│   │   └── actions           [N]       'open' 或 'close'
│   ├── wrist_zed.avi                   ZED-M 左眼, 1280x720
│   └── third_rs.avi                    RealSense RGB, 640x480（或实际分辨率）
└── replay/
    ├── joint_trajectory.npz
    │   ├── timestamps        [T']      相对时刻
    │   └── joint_positions   [T', 7]   实际执行的关节角
    ├── joint_velocities.npz
    │   ├── timestamps        [T'']
    │   └── velocities        [T'', 7]  关节速度（弧度/秒）
    ├── end_effector_pose.npz
    │   ├── timestamps        [T''']
    │   ├── positions         [T''', 3] EEF 位置 (x, y, z)，单位米
    │   └── quaternions       [T''', 4] EEF 姿态 (qx, qy, qz, qw)
    ├── gripper_events.npz
    │   ├── relative_times    [M]       实际发出夹爪指令的时刻
    │   └── actions           [M]
    ├── wrist_zed.avi                   ZED-M 左眼, 1280x720
    └── third_rs.avi                    RealSense RGB
```

### 读取数据示例

```python
import numpy as np

# 读取 replay 关节轨迹
d = np.load("traj_0/replay/joint_trajectory.npz")
print(f"Duration: {d['timestamps'][-1]:.2f}s")
print(f"Joint positions shape: {d['joint_positions'].shape}")  # (T, 7)

# 读取 EEF 姿态
ee = np.load("traj_0/replay/end_effector_pose.npz")
print(f"EEF positions shape: {ee['positions'].shape}")   # (T, 3) in meters
print(f"EEF quaternion shape: {ee['quaternions'].shape}") # (T, 4)

# 读取夹爪事件
g = np.load("traj_0/teach/gripper_events.npz", allow_pickle=True)
for t, a in zip(g['relative_times'], g['actions']):
    print(f"  t={t:.2f}s: gripper {a}")

# 加载视频
import cv2
cap = cv2.VideoCapture("traj_0/replay/wrist_zed.avi")
ret, frame = cap.read()  # frame.shape = (720, 1280, 3)
```

---

## 单独使用 ZED-M 工具

### 检测设备

```bash
bash scripts/find_zed_device.sh
# 输出: /dev/video4（或其他编号）

python3 scripts/find_zed_device.py
# 同上
```

### 采集左目图片序列

```bash
python3 scripts/collect_zed_mono_images.py \
  --out data/zed_left \
  --side left \
  --preview
```

输出文件格式：
```
data/zed_left/
├── 000000_1710000000.123456.jpg
├── 000001_1710000000.157000.jpg
└── ...
```

### 录制视频

```bash
python3 scripts/record_zed_mono_video.py \
  --out zed_left.mp4 \
  --side left \
  --preview
```

---

## ROS2 发布 ZED-M 图像 topic

### 安装 ROS2 包

```bash
cd ~/chenyu/data_collection/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select zed_mono_v4l2
source install/setup.bash
```

### 运行节点

```bash
# 发布左目
ros2 run zed_mono_v4l2 zed_mono_node --ros-args \
  -p device:=auto \
  -p side:=left \
  -p topic:=/zedm/left/image_raw \
  -p frame_id:=zedm_left_camera

# 发布右目
ros2 run zed_mono_v4l2 zed_mono_node --ros-args \
  -p side:=right \
  -p topic:=/zedm/right/image_raw \
  -p frame_id:=zedm_right_camera
```

### 查看图像

```bash
ros2 topic list | grep zedm
ros2 run rqt_image_view rqt_image_view
# 在界面中选择 /zedm/left/image_raw
```

### 录制 ROS2 bag

```bash
# 只录 ZED-M
ros2 bag record -o zedm_left_bag /zedm/left/image_raw

# 同步录制机械臂状态 + ZED-M + RealSense
ros2 bag record -o demo_bag \
  /zedm/left/image_raw \
  /camera/color/image_raw \
  /joint_states \
  /franka_robot_state_broadcaster/robot_state \
  /tf /tf_static
```

---

## 常见启动命令参数

### teach_replay_robotiq.py 完整参数

```
--output_dir     数据存储根目录          默认: ~/chenyu/data_collection/data
--fps            相机录制帧率            默认: 30
--record_rate    关节采样频率 (Hz)       默认: 100
--realsense_topic  RealSense图像话题    默认: /camera/color/image_raw
--zed_device     ZED-M设备 (auto|/dev/videoX)  默认: auto
--zed_side       使用哪只眼 (left|right)  默认: left
--no_wrist_camera  禁用ZED-M录像
--no_third_camera  禁用RealSense录像
--trajectory_smoothing_window  平滑窗口大小  默认: 11
```

### 不带相机的纯关节采集

```bash
python3 teach_collect/teach_replay_robotiq.py \
  --no_wrist_camera \
  --no_third_camera \
  --output_dir ~/chenyu/data_collection/data
```

### 只用右眼 ZED-M

```bash
python3 teach_collect/teach_replay_robotiq.py \
  --zed_side right \
  --output_dir ~/chenyu/data_collection/data
```

---

## 故障排除

### ZED-M 找不到

**症状：** `ZED-M not found` 或 wrist camera disabled

**检查：**
```bash
# 必须看到 2b03:f682 (video) 和 2b03:f681 (HID)
lsusb | grep -i -E "zed|stereo|2b03"

# 如果只有 f681 没有 f682：
# → 换 USB3 口（蓝色口），用 USB3 线，不经过 Hub
# → 重新插拔后再检查

v4l2-ctl --list-devices   # 确认 ZED-M 出现
ffplay /dev/video4         # 替换为实际编号，快速验证
```

### Robotiq 夹爪不响应

**症状：** 按 o/c 无反应，或日志报错

**检查：**
```bash
# 在 Robotiq 驱动终端确认已激活
ros2 action list | grep robotiq
# 应看到: /robotiq_gripper_controller/gripper_cmd

# 手动测试
ros2 action send_goal /robotiq_gripper_controller/gripper_cmd \
  control_msgs/action/GripperCommand \
  "{command: {position: 0.0, max_effort: 50.0}}"
```

如果没有 action server：
```bash
# 检查 robotiq_ws 是否已 source
source ~/chenyu/robotiq_ws/install/setup.bash

# 确认驱动正在运行
ros2 node list | grep robotiq
```

### RealSense 视频无法录制

**症状：** `No RealSense frame yet — skipping RS recording`

**检查：**
```bash
ros2 topic hz /camera/color/image_raw  # 应约 30 Hz

# 如果无数据，确认 RealSense 节点在运行
ros2 node list | grep realsense
ros2 topic list | grep camera
```

更改 topic 名称：
```bash
python3 teach_replay_robotiq.py \
  --realsense_topic /camera/rgb/image_raw  # 根据实际 topic 调整
```

### 机械臂拖不动

**症状：** TEACH 模式下感觉关节很硬

**检查：**
- 外部使能装置（脚踏板）是否踩下？必须踩下才能运动
- 机械臂是否处于错误状态（臂底座 LED 红色/橙色）？
- teach_replay 控制栈是否正常运行？

```bash
ros2 topic list | grep teach_replay
# 应看到: /teach_replay/mode, /teach_replay/replay_started, ...
```

### 关节数据为空

**症状：** 教学时 `teach_times` 为空，保存失败

**检查：**
```bash
ros2 topic echo /joint_states | head -20
# 应看到 fr3_joint1-7 的数据
```

---

## 推荐采集流程

### 短期（每次采集 30 分钟）

1. 启动所有硬件（步骤 1-4）
2. 启动主采集脚本，输入 session 名称（如 `pick_cup_20260521`）
3. 采集 5-10 条轨迹
4. 验证数据：`ls -lh data/pick_cup_20260521/`
5. 停止（按 q）

### 单条轨迹时间分配

```
按 t 进入教学 (1秒)
拖动机械臂完成任务 (15-45秒)
关键点停顿0.5-1秒
按夹爪键 (1-2秒)
按 s 保存 (1秒)
按 r 回放 (任务时长 + 5秒)
按 1 保存 (1秒)
--------------------
总计: ~50-80 秒/条轨迹
预期: ~40 条/小时
```

---

## 硬件说明

### Robotiq 2F-85 夹爪参数

| 参数 | 值 |
|------|----|
| 最大开口 | 85 mm = 0.085 m |
| 完全张开 position | 0.000 m |
| 完全闭合 position | 0.085 m |
| 控制接口 | `/robotiq_gripper_controller/gripper_cmd` |
| 动作类型 | `control_msgs/action/GripperCommand` |
| 串口 | `/dev/ttyUSB0`（可能变化，见步骤 1）|

### ZED-M 相机参数

| 参数 | 值 |
|------|----|
| 双目拼接分辨率 | 2560×720（左+右各 1280×720）|
| 可用帧率 | 15/30/60/100 Hz |
| 默认采集 | 2560×720 @30fps |
| 存储格式 | 切出左眼 1280×720 → AVI |
| USB 要求 | USB 3.0 蓝色口，USB 3.0 线 |

### RealSense D435 参数

| 参数 | 值 |
|------|----|
| RGB 分辨率 | 640×480 或 1280×720 |
| 帧率 | 30 Hz |
| ROS2 topic | `/camera/color/image_raw` |
| 存储格式 | AVI（BGR8）|

---

## 分析数据

### 快速统计

```python
#!/usr/bin/env python3
from pathlib import Path
import numpy as np

session_dir = Path("data/pick_cup_20260521")
trajs = sorted(session_dir.glob("traj_*/replay/joint_trajectory.npz"))

print(f"Total trajectories: {len(trajs)}")
lengths = []
for p in trajs:
    d = np.load(p)
    T = len(d['timestamps'])
    lengths.append(T)
    print(f"  {p.parent.parent.name}: {T} steps ({d['timestamps'][-1]:.1f}s)")

print(f"Mean: {np.mean(lengths):.1f}  Min: {np.min(lengths)}  Max: {np.max(lengths)}")
```

### 检查 EEF 轨迹

```python
import numpy as np
import matplotlib.pyplot as plt

ee = np.load("data/pick_cup/traj_0/replay/end_effector_pose.npz")
t = ee['timestamps']
xyz = ee['positions']

plt.figure(figsize=(12, 4))
for i, label in enumerate(['X', 'Y', 'Z']):
    plt.subplot(1, 3, i+1)
    plt.plot(t, xyz[:, i])
    plt.xlabel('Time (s)')
    plt.ylabel(f'{label} (m)')
    plt.title(f'EEF {label}')
plt.tight_layout()
plt.savefig('eef_trajectory.png')
```

---

## 每日操作速查

```bash
# 1. 检查硬件
lsusb | grep -i -E "zed|stereo|2b03"   # ZED-M
ls /dev/ttyUSB*                          # Robotiq

# 2. Robotiq 驱动（终端A，保持运行）
cd ~/chenyu/robotiq_ws && source /opt/ros/humble/setup.bash && source install/setup.bash
ros2 launch robotiq_description robotiq_control.launch.py com_port:=/dev/ttyUSB0 launch_rviz:=false

# 3. Franka 控制栈（终端B，保持运行）
cd ~/franka_ros2_ws && source /opt/ros/humble/setup.bash && source install/setup.bash
ros2 launch franka_bringup teach_replay.launch.py

# 4. RealSense（终端C，如果未启动）
source /opt/ros/humble/setup.bash
ros2 launch realsense2_camera rs_launch.py

# 5. 主采集（终端D）
cd ~/chenyu/data_collection
source /opt/ros/humble/setup.bash && source ~/franka_ros2_ws/install/setup.bash && source ~/chenyu/robotiq_ws/install/setup.bash
python3 teach_collect/teach_replay_robotiq.py --output_dir data

# 6. 采集完毕后检查数据
find data/<session>/ -name "*.npz" | xargs ls -lh
find data/<session>/ -name "*.avi" | xargs ls -lh
```
