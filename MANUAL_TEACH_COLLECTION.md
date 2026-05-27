# Manual Teaching Mode Data Collection

**Alternative Method:** Hand-dragging the robot arm to record trajectories  
**vs DROID VR Teleoperation (Oculus-based)**

---

## Overview

Franka 官方提供了 **teach_replay** 模式：

1. **TEACH 模式** — 零重力补偿，用手直接拖动机械臂
   - 机械臂被动地跟随你的手动运动
   - 实时记录关节位置、速度、末端执行器姿态
   - 可通过键盘控制夹爪（按 'o' 打开，'c' 关闭）

2. **REPLAY 模式** — 自动重放刚才录制的轨迹
   - 机械臂精确执行教学轨迹
   - 同时记录实际执行的关节位置、速度、EE 姿态
   - 可选：录制视频

**优点：**
- ✅ 不需要 VR 头盔，操作更直观
- ✅ 直接用手感受力反馈，更精确控制
- ✅ 数据采集和回放分离（可验证）
- ✅ 录制视频便于事后验证

**缺点：**
- ❌ 需要物理靠近机械臂（VR 更远程）
- ❌ 逐个轨迹教学，效率相对低
- ❌ 需要手动标记夹爪事件时刻

---

## 快速开始

### 前置条件

```bash
ssh robot
cd ~/franka_ros2_ws

# 源环境变量
source /opt/ros/humble/setup.bash
source install/setup.bash
```

### 启动 Teach-Replay 系统

**终端 1：启动 ROS 2 控制栈**

```bash
ros2 launch franka_bringup teach_replay.launch.py
# 这启动了 teach_replay_controller，等待模式指令
```

**终端 2：启动交互式采集脚本**

```bash
python3 src/franka_example_controllers/scripts/teach_replay_orchestrator.py \
  --output_dir ~/hebu/robot_recordings \
  --fps 30 \
  --record_rate 100
```

**会提示输入：**
```
enter save data folder name: (e.g., "pick_cup_attempt_1")
```

### 采集工作流

**键盘指令:**

| 按键 | 动作 | 说明 |
|------|------|------|
| **t** | 进入 TEACH 模式 | 机械臂零扭矩，可手动拖动 |
| **o** | 打开夹爪 | 仅在 TEACH 模式下 |
| **c** | 关闭夹爪 | 仅在 TEACH 模式下 |
| **s** | 保存轨迹 | 结束 TEACH，准备 REPLAY |
| **r** | 回放轨迹 | 执行刚才记录的运动 |
| 1 或 s | 保存回放 | 保存此次回放的记录 |
| 2 或 d | 丢弃 | 丢弃此次回放，保留教学轨迹 |
| 3 或 r | 重新回放 | 再播放一次（覆盖之前的回放记录） |
| **h** | 回原点 | 夹爪回原点 |
| **q** | 退出 | 结束采集 |

---

## 详细步骤

### 1. 机械臂重力补偿（TEACH 模式）

```
[按 t]
状态: IDLE -> TEACHING
机械臂进入零重力补偿状态
```

此时：
- 机械臂上所有关节的扭矩被设为 0（仅补偿自重）
- 你可以用手轻轻推动机械臂，它会被动跟随
- 脚踏板仍需要踩下以启用运动

### 2. 拖动机械臂录制轨迹

**在 TEACH 模式下（已按 t）：**

1. 踩下**外部使能装置**（脚踏板或按钮）
2. 用手轻轻拖动机械臂 EEF 移动到目标位置
   - 从起始点 → 中间点 1 → 中间点 2 → ... → 终点
   - 每个点停留 0.5-1 秒以便采样
   - 速度应该平稳，不要突然加速/减速

3. **夹爪控制**（如需要）
   - 按 **c** 关闭夹爪
   - 等待 1-2 秒
   - 继续移动
   - 按 **o** 打开夹爪

**示例：Pick-up 任务**
```
[按 t 进入 TEACH]
[踩脚踏板]
[拖机械臂靠近物体，约 3 秒]
[按 c 关闭夹爪，等 1 秒]
[拖机械臂抬起，向上 5 秒]
[拖机械臂移到放置位置，2 秒]
[按 o 打开夹爪，等 1 秒]
[拖机械臂离开，2 秒]
[释放脚踏板]
总耗时：~14 秒
```

### 3. 保存教学轨迹

```
[按 s]
状态: TEACHING -> READY
教学轨迹已保存到 teach/joint_trajectory.npz
```

此时保存的文件：
```
session_dir/teach/
├── joint_trajectory.npz      # 关节位置 [T, 7]
└── gripper_events.npz        # 夹爪事件 [(rel_time, action), ...]
```

### 4. 回放验证

```
[按 r]
状态: READY -> REPLAYING
机械臂开始自动执行刚才的轨迹
```

此时：
- 机械臂**主动**执行教学的轨迹
- 脚踏板无需踩下（自动运动）
- 系统自动录制：
  - 实际执行的关节位置
  - 实际执行的关节速度
  - 实际执行的 EE 姿态
  - 视频（可选）

**所有 REPLAY 数据保存到：**
```
session_dir/replay/
├── joint_trajectory.npz      # 实际执行的关节位置 [T, 7]
├── joint_velocities.npz      # 实际执行的关节速度 [T, 7]
├── end_effector_pose.npz     # 实际 EE 姿态 [T, 7] (x,y,z,qx,qy,qz,qw)
├── gripper_events.npz        # 夹爪事件时刻
└── recording.avi             # 视频录制（可选）
```

### 5. 审查和保存

```
[按 s 或 1]
状态: REVIEW
保存此次 REPLAY 记录
traj_N 文件夹完成
```

**或者不保存重做：**
```
[按 d 或 2]
状态: REVIEW -> READY
丢弃此次 REPLAY，但保留 TEACH 轨迹
再按 r 可重新 REPLAY（覆盖）
```

---

## 数据保存结构

```
~/hebu/robot_recordings/
└── <save_data_folder>/
    ├── traj_0/
    │   ├── teach/
    │   │   ├── joint_trajectory.npz
    │   │   │   ├── timestamps [T]        # 采样时刻（绝对，秒）
    │   │   │   ├── joint_positions [T, 7]  # 关节角（弧度）
    │   │   │   └── gripper_widths [T]   # 夹爪宽度（米）
    │   │   └── gripper_events.npz
    │   │       ├── relative_times [N]    # 相对时刻（秒）
    │   │       └── actions [N]           # 'open' 或 'close'
    │   │
    │   └── replay/
    │       ├── joint_trajectory.npz
    │       │   ├── timestamps [T']
    │       │   ├── joint_positions [T', 7]
    │       │   └── gripper_widths [T']
    │       ├── joint_velocities.npz
    │       │   ├── timestamps [T'']
    │       │   └── velocities [T'', 7]
    │       ├── end_effector_pose.npz
    │       │   ├── timestamps [T''']
    │       │   ├── positions [T''', 3]   # x, y, z (米)
    │       │   └── quaternions [T''', 4] # qx, qy, qz, qw
    │       ├── gripper_events.npz
    │       │   ├── timestamps [M]        # 发送夹爪指令的时刻
    │       │   └── actions [M]
    │       └── recording.avi             # 视频（如启用）
    │
    ├── traj_1/
    │   └── ...
    └── ...
```

---

## 启动命令详解

### 基本命令

```bash
python3 teach_replay_orchestrator.py
```

### 常用参数

```bash
python3 teach_replay_orchestrator.py \
  --output_dir ~/hebu/robot_recordings \      # 输出目录
  --fps 30 \                                  # 视频帧率（如录制）
  --record_rate 100 \                         # 关节采样率（Hz）
  --image_topic /camera/rgb/image_raw \       # 摄像头话题
  --trajectory_smoothing_window 11 \          # 平滑窗口（奇数）
  --no_video                                  # 禁用视频录制（加快采集）
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--fps` | 30 | 视频录制帧率（视频文件中） |
| `--record_rate` | 100 | 关节状态采样频率（Hz，实际采集率） |
| `--output_dir` | `~/robot_recordings` | 保存根目录 |
| `--image_topic` | `/camera/rgb/image_raw` | 图像话题（可选） |
| `--trajectory_smoothing_window` | 11 | 平滑窗口大小（奇数） |
| `--raw_image` | False | 使用原始图像而非压缩 |
| `--no_video` | False | 禁用视频录制 |

---

## 与 DROID VR 方式的对比

| 特性 | Teach-Replay（手动） | DROID VR（Oculus） |
|------|--------|---------|
| **需要 VR 头盔** | ❌ | ✅ |
| **需要物理接触** | ✅ | ❌ |
| **力反馈** | ✅ 直接 | ⚠️ 间接 |
| **采集速度** | 慢（逐个轨迹） | 快（连续） |
| **每条轨迹耗时** | 20-120 秒 | 20-120 秒 |
| **setup 复杂度** | 低 | 中 |
| **数据质量** | 高（直接控制） | 高（VR 可重复性好） |
| **视频录制** | ✅ 可选 | ✅ 内置（.svo） |
| **直观程度** | ✅ 很直观 | ⚠️ 需要适应 |
| **单人可操作** | ✅ | ✅ |

---

## 数据读取示例

### 读取 TEACH 轨迹

```python
import numpy as np

# 加载教学阶段的轨迹
teach_traj = np.load("traj_0/teach/joint_trajectory.npz")
timestamps = teach_traj['timestamps']  # [T] 秒
joint_pos = teach_traj['joint_positions']  # [T, 7] 弧度
gripper_width = teach_traj['gripper_widths']  # [T] 米

print(f"Teach trajectory length: {len(timestamps)} frames @ {1/(timestamps[1]-timestamps[0]):.1f} Hz")

# 夹爪事件
teach_events = np.load("traj_0/teach/gripper_events.npz")
event_times = teach_events['relative_times']  # [N] 相对秒
actions = teach_events['actions']  # [N] 字符串数组 ('open' 或 'close')

for t, action in zip(event_times, actions):
    print(f"  t={t:.2f}s: gripper {action}")
```

### 读取 REPLAY 轨迹

```python
# 加载回放阶段的实际执行轨迹
replay_traj = np.load("traj_0/replay/joint_trajectory.npz")
replay_timestamps = replay_traj['timestamps']
replay_joint_pos = replay_traj['joint_positions']

# 末端执行器姿态（由状态广播器记录）
ee_pose = np.load("traj_0/replay/end_effector_pose.npz")
ee_timestamps = ee_pose['timestamps']
ee_pos = ee_pose['positions']  # [T, 3] m
ee_quat = ee_pose['quaternions']  # [T, 4] [qx, qy, qz, qw]

# 关节速度（导数）
joint_vel = np.load("traj_0/replay/joint_velocities.npz")
vel_timestamps = joint_vel['timestamps']
velocities = joint_vel['velocities']  # [T, 7] rad/s

# 比较教学 vs 实际
print(f"Teach duration: {timestamps[-1] - timestamps[0]:.2f}s")
print(f"Replay duration: {replay_timestamps[-1] - replay_timestamps[0]:.2f}s")
```

### 转换为 HDF5（用于训练）

```bash
cd ~/hebu/robot_recordings

# 若干采集的 traj_* 目录已有 teach/ 和 replay/ 子目录
# 用现有脚本转换

python scripts/build_pickcup_h5.py \
  --input_dir <save_data_folder> \
  --output_h5 pickcup_manual_teaching.h5
```

---

## 故障排除

### 问题：机械臂无法进入 TEACH 模式

**症状:** 按 t 无反应，或显示"Mode change failed"

**原因:**
- ROS 2 控制栈未启动
- teach_replay_controller 未正确加载
- 机械臂在错误状态（紧急停止？）

**解决:**
```bash
# 终端 1 检查
ros2 node list | grep teach_replay
ros2 topic list | grep teach_replay

# 若无此话题，重新启动
ros2 launch franka_bringup teach_replay.launch.py
```

### 问题：手拖不动机械臂

**症状:** 即使在 TEACH 模式，也感觉很硬

**原因:**
- 脚踏板未踩下（外部使能装置）
- 机械臂仍在使能但未进入零重力补偿
- 夹爪被卡住

**解决:**
```bash
# 检查脚踏板状态
ros2 topic echo /franka_robot_state_broadcaster/robot_state | grep external_controller_connected

# 若为 False，踩下脚踏板
# 若为 True 仍无反应，检查机械臂是否在错误状态
```

### 问题：教学轨迹保存后没有文件

**症状:** 按 s 后，traj_N/ 目录为空

**原因:**
- 文件系统权限问题
- 采集时间太短（无数据采样）
- 脚踏板在 TEACH 期间一直没踩下

**解决:**
```bash
# 检查目录权限
ls -la ~/hebu/robot_recordings/<folder>/

# 重新采集，确保脚踏板踩下至少 2-3 秒
```

### 问题：REPLAY 时机械臂突然停止

**症状:** 回放中途机械臂停止运动

**原因:**
- 发生碰撞检测触发
- 脚踏板被释放
- 网络中断

**解决:**
```bash
# 检查机械臂状态
ros2 topic echo /franka_robot_state_broadcaster/robot_state | head -20

# 若显示 errors，按机械臂上的复位按钮（蓝色）
# 重新启动 REPLAY
```

---

## 最佳实践

### 教学阶段

1. **动作平稳** — 避免突然加速/减速
2. **停顿足够** — 在关键点停留 0.5-1 秒
3. **不要过快** — 手工教学通常 5-15 秒/个动作
4. **记录事件** — 及时按 o/c 标记夹爪事件

### 回放验证

5. **首次回放观察** — 看是否正常执行
6. **多次回放** — 多次 REPLAY 以验证重复性
7. **不满意就重做** — 按 d 丢弃，再按 r 重播

### 数据收集

8. **多样化** — 同一任务收集 20-50 条不同的演示
9. **变化场景** — 改变物体位置、起始姿态等
10. **备份** — 定期备份到外部存储

---

## 与现有数据集整合

**现有数据集：** 113 条 pick-cup 演示（DROID VR 采集）

**整合新的手工教学数据：**

```bash
# 1. 用 teach_replay_orchestrator.py 采集新数据到 my_hand_teaching/
#    目录中会有 traj_0, traj_1, ... 等

# 2. 转换为 HDF5
cd ~/hebu/robot_recordings
python scripts/build_pickcup_h5.py \
  --input_dir my_hand_teaching \
  --output_h5 hand_teaching_demos.h5

# 3. 合并到现有数据集
python << 'EOF'
import h5py

# 打开现有和新数据
with h5py.File("pickcup_256_256.h5", "r+") as old_h5:
    num_old = len(old_h5)  # 现有 demo 数
    
with h5py.File("hand_teaching_demos.h5", "r") as new_h5:
    with h5py.File("pickcup_256_256_combined.h5", "w") as combined:
        # 复制现有
        with h5py.File("pickcup_256_256.h5", "r") as old:
            for key in old.keys():
                old[key].copy(combined, key)
        
        # 追加新数据（重新编号为 demo_113, demo_114, ...)
        for i, key in enumerate(new_h5.keys()):
            new_idx = num_old + i
            new_h5[key].copy(combined, f"demo_{new_idx}")

print(f"Combined: {num_old} old + {len(new_h5)} new = {num_old + len(new_h5)} demos")
EOF
```

---

## 参考资源

- **脚本位置:** `/home/robot/franka_ros2_ws/src/franka_example_controllers/scripts/teach_replay_orchestrator.py`
- **Launcher:** `/home/robot/franka_ros2_ws/src/franka_bringup/launch/teach_replay.launch.py`
- **Controller:** `/home/robot/franka_ros2_ws/src/franka_example_controllers/` (TeachReplayController C++)

---

**关键区别总结：**

- **DROID VR**: 适合高速采集、VR 沉浸感强、需要头盔
- **Teach-Replay**: 适合精确控制、直观、适合单条轨迹调整优化

**推荐用法:**
- 初期数据采集：**Teach-Replay**（更容易上手）
- 大规模采集：**DROID VR**（效率更高）
- 质量优化：**Teach-Replay**（精细调整）
