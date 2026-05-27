# 启动指南

## 步骤 0（必须）— 激活 Franka FCI

**每次开机后第一件事**，否则 Franka 控制栈无法启动：

1. 浏览器打开 `https://172.16.0.2`（忽略证书警告）
2. 解锁机器人（右下角锁头图标）
3. 找到 **FCI** 开关 → 点击 **Enable FCI / Activate FCI**
4. 确认状态变为绿色/蓝色 active

> 机械臂底座 LED 变**蓝色**后表示 FCI 已激活。

验证连通性（可选）：
```bash
source ~/franka_ros2_ws/install/setup.bash
~/franka_ros2_ws/install/libfranka/bin/echo_robot_state 172.16.0.2
# 应该打印机器人状态，而不是 "Connection refused"
```

---

## 前置检查

```bash
lsusb | grep -i -E "zed|stereo|2b03"   # 必须看到 2b03:f682 + 2b03:f681
ls /dev/ttyUSB*                          # 必须看到 /dev/ttyUSB0
v4l2-ctl --list-devices                  # 确认 ZED-M 出现
```

---

## 终端 A — Robotiq 夹爪驱动

```bash
cd ~/chenyu/robotiq_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch robotiq_description robotiq_control.launch.py \
  com_port:=/dev/ttyUSB0 \
  launch_rviz:=false
```

等待：
```
Robotiq Gripper successfully activated!
```

---

## 终端 B — Franka 控制栈

```bash
cd ~/franka_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch franka_bringup teach_replay.launch.py
```

等待日志稳定，看到 `teach_replay_controller` 成功激活。

> **注意：** `franka.config.yaml` 里 `load_gripper` 已设为 `"false"`（机械臂末端为 Robotiq，没有 Franka Hand）。

---

## 终端 C — RealSense 相机（有线时才启动）

```bash
source /opt/ros/humble/setup.bash
ros2 launch realsense2_camera rs_launch.py
```

验证：
```bash
ros2 topic hz /camera/color/image_raw   # 应约 30 Hz
```

> 没有 RealSense 时，主采集脚本加 `--no_third_camera` 跳过。

---

## 终端 D — 主采集脚本

**有 RealSense：**
```bash
cd ~/chenyu/data_collection
source /opt/ros/humble/setup.bash
source ~/franka_ros2_ws/install/setup.bash
source ~/chenyu/robotiq_ws/install/setup.bash

python3 teach_collect/teach_replay_robotiq.py \
  --output_dir data \
  --fps 30 \
  --record_rate 100
```

**无 RealSense：**
```bash
python3 teach_collect/teach_replay_robotiq.py \
  --output_dir data \
  --fps 30 \
  --record_rate 100 \
  --no_third_camera
```

输入 session 名称（如 `pick_cup_20260522`），然后按键操作：

| 按键 | 动作 |
|------|------|
| `t` | 开始教学（进入零力矩模式） |
| `o` | 夹爪打开 |
| `c` | 夹爪关闭 |
| `s` | 停止并保存教学 |
| `r` | 回放 |
| `1` | 保存回放，准备下一条 |
| `2` | 丢弃回放 |
| `3` | 重新回放 |
| `q` | 退出 |

> ⚠️ TEACH 模式需踩下脚踏板（外部使能装置）才能拖动机械臂。

---

## 一条轨迹标准流程

```
t → 拖动机械臂 → c（抓取）→ 拖动 → o（放置）→ s → r → 观察 → 1
```

---

## 采集完毕验证

```bash
find data/<session>/ -name "*.npz" | xargs ls -lh
find data/<session>/ -name "*.avi" | xargs ls -lh
```

---

## 常见问题

| 症状 | 原因 | 解决 |
|------|------|------|
| `ros2_control_node` 崩溃 (exit -6) | FCI 未激活 | 步骤 0，激活 FCI |
| `Connection to FCI refused` | 同上 | 同上 |
| `Robotiq Gripper` 无反应 | ttyUSB 权限或串口错误 | `ls /dev/ttyUSB*`，确认 `/dev/ttyUSB0` |
| ZED-M not found | USB3 口未插或用了 Hub | 换蓝色 USB3 直插 |
| `No RealSense devices` | 相机未连接 | 加 `--no_third_camera` 跳过 |
