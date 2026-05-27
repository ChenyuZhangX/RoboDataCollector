# Data Collection Methods Comparison & Quick Guide

**At a glance:** Two complementary ways to collect robot manipulation data

---

## 快速选择表

```
需要采集大量数据？         → 用 VR (DROID)
想要精确控制和调试？        → 用手动拖动 (Teach-Replay)
没有 VR 头盔？             → 用手动拖动 (Teach-Replay)
想要沉浸感和高效率？        → 用 VR (DROID)
第一次用机械臂采集？        → 用手动拖动 (Teach-Replay)
已有 113 条 VR 数据了？     → 用手动拖动补充
```

---

## 对比详表

| 维度 | **Teach-Replay（手动）** | **DROID VR（遥操）** | 推荐用途 |
|------|--------|---------|---------|
| **启动时间** | ~2 min | ~5 min | 🟢 手动 |
| **硬件需求** | 无 VR | Oculus + PC | 🟢 手动 |
| **每条轨迹时间** | 20-120 秒 | 20-120 秒 | 平手 |
| **单小时采集条数** | ~20-30 条 | ~30-50 条 | 🔵 VR |
| **力反馈** | ✅ 直接触觉 | ⚠️ 无 | 🟢 手动 |
| **控制精度** | 📍 极高（直接） | 📍 高（通过 VR） | 🟢 手动 |
| **学习曲线** | 📈 低（直观） | 📈 中（需适应） | 🟢 手动 |
| **可重复性** | 📊 中 | 📊 高（VR 稳定） | 🔵 VR |
| **视频录制** | ✅ 可选 | ✅ 自动 .svo | 🔵 VR |
| **多人采集** | ✅ 支持 | ⚠️ 单人体验 | 平手 |
| **远程操控** | ❌ 需要物理靠近 | ✅ VR 可远程 | 🔵 VR |
| **数据文件大小** | 500 MB | 500 MB - 1 GB | 平手 |
| **后期处理** | NPZ 手动转 HDF5 | HDF5 + SVO 转 MP4 | 🔵 VR |
| **适合新手** | ✅ 最适合 | ⚠️ 需要习惯 | 🟢 手动 |
| **适合大规模** | ❌ 效率低 | ✅ 效率高 | 🔵 VR |

---

## 两种方法的工作流对比

### Teach-Replay（手动拖动）流程

```
1. 启动控制栈
   └─ ros2 launch franka_bringup teach_replay.launch.py

2. 启动采集脚本
   └─ python3 teach_replay_orchestrator.py

3. 交互式工作流
   ├─ [t] 进入 TEACH 模式（零重力补偿）
   ├─ [踩脚踏板] 启用运动
   ├─ [手拖 EEF] 执行动作序列（20-120 秒）
   ├─ [按 o/c] 控制夹爪（可选）
   ├─ [s] 保存教学轨迹
   ├─ [r] 回放验证
   ├─ [1] 保存数据
   └─ 重复或 [q] 退出

输出：traj_N/teach/ + traj_N/replay/
```

### DROID VR 工作流

```
1. 启动控制栈
   └─ 自动启动（通过 droid 脚本）

2. 启动 GUI
   └─ python scripts/main.py --right_controller

3. GUI 驱动工作流
   ├─ 登录 (输入用户名)
   ├─ 场景配置 (选择任务)
   ├─ 摄像头验证 (检查 3 台 ZED)
   ├─ [穿上 VR]
   ├─ [VR 手位置] → 机械臂运动
   ├─ [按 trigger] 开始/停止录制
   ├─ [标记成功/失败]
   └─ 自动保存

输出：data/success|failure/<date>/<timestamp>/
```

---

## 典型采集场景

### 场景 A：初期数据采集（新项目）

```
选择：Teach-Replay
理由：
  - 不需要 VR 头盔（可能还没购置）
  - 操作员快速上手
  - 可精细调整每条轨迹
  - 前 20-50 条数据用来验证任务定义

流程：
  Day 1: 采集 30 条轨迹（3-4 小时）
  Day 2: 审查数据质量，微调采集策略
  Day 3: 再采集 20 条补充数据
  结果: ~50 条演示 → 训练小规模模型做概念验证
```

### 场景 B：大规模生成（需要 1000+ 条数据）

```
选择：DROID VR
理由：
  - 采集速度快（~40-50 条/小时）
  - 可多人轮流采集
  - VR 提供沉浸感，重复性好
  - 自动生成高质量视频

流程：
  Week 1: 采集 200 条（5 小时）
  Week 2: 采集 400 条（10 小时）
  Week 3: 采集 400 条 + 数据清洗
  结果: ~1000 条演示 → 训练生产级扩散策略
```

### 场景 C：混合方法（推荐）

```
初期：Teach-Replay
  ├─ 采集 50 条演示
  ├─ 构建初步数据集
  └─ 验证采集管线和数据格式

中期：DROID VR
  ├─ 采集 400 条演示
  ├─ 快速扩展数据
  └─ 提升多样性

后期：Teach-Replay（微调）
  ├─ 针对模型错误场景采集 20-50 条
  ├─ 精确控制，高精度数据
  └─ 增强学习反馈

总计：~500 条演示（分阶段完成）
```

---

## 每种方法的关键命令

### Teach-Replay 快速命令

```bash
# 启动主系统
ros2 launch franka_bringup teach_replay.launch.py &

# 启动采集脚本
python3 ~/franka_ros2_ws/src/franka_example_controllers/scripts/teach_replay_orchestrator.py \
  --output_dir ~/hebu/robot_recordings \
  --fps 30 \
  --record_rate 100 \
  --no_video  # 加速采集

# 或带视频
python3 teach_replay_orchestrator.py \
  --fps 30 \
  --image_topic /camera/rgb/image_raw
```

### DROID VR 快速命令

```bash
# 源环境
source ~/franka_ros2_ws/install/setup.bash

# 启动 GUI
cd ~/franka_ros2_ws/droid_setup/droid
python scripts/main.py --right_controller

# 或左手控制
python scripts/main.py --left_controller
```

---

## 数据质量对比

### Teach-Replay 采集的数据特性

```
优势：
  ✅ 关节轨迹平滑（直接记录手动运动）
  ✅ 力反馈真实（通过触觉感知）
  ✅ 夹爪事件精确（手动标记）
  ✅ 姿态准确（基于正向运动学）

劣势：
  ⚠️ 人为变动性大（每次拖动不同）
  ⚠️ 重复性相对低（无法完全复现）
  ⚠️ 回放可能有偏差（机械臂跟踪误差）
```

### DROID VR 采集的数据特性

```
优势：
  ✅ 多人一致性好（VR 映射固定）
  ✅ 重复性高（相同的虚拟映射）
  ✅ 视频质量高（.svo 自动录制）
  ✅ 元数据完整（自动时间戳）

劣势：
  ⚠️ VR 映射可能有偏差
  ⚠️ 需要适应期（学习 VR 控制）
  ⚠️ 数据文件较大（含视频）
```

---

## 数据处理流程对比

### Teach-Replay 后期处理

```
raw data (traj_N/)
    ↓
verify NPZ 结构 (teach/ + replay/)
    ↓
build_pickcup_h5.py (聚合为单个 HDF5)
    ↓
训练数据集
```

**命令：**
```bash
python scripts/build_pickcup_h5.py --input_dir <folder> --output_h5 out.h5
```

### DROID VR 后期处理

```
raw data (data/success/)
    ↓
postprocess.py
    ├─ SVO → MP4 转换
    ├─ 元数据验证
    └─ S3 上传 (可选)
    ↓
build_pickcup_h5.py (可选，转换为训练格式)
    ↓
训练数据集
```

**命令：**
```bash
python scripts/postprocess.py
python scripts/build_pickcup_h5.py --input_dir data/success/
```

---

## 性能指标

### 采集速度

| 方法 | 每小时轨迹数 | 每天产能（8小时） | 采集 100 条需时间 |
|------|--------|---------|---------|
| Teach-Replay | ~25-30 条 | ~200-240 条 | 3.3-4 小时 |
| DROID VR | ~40-50 条 | ~320-400 条 | 2-2.5 小时 |

### 存储需求

| 方法 | 每条轨迹大小 | 100 条总大小 | 1000 条总大小 |
|------|--------|---------|---------|
| Teach-Replay（无视频） | ~300-500 MB | 30-50 GB | 300-500 GB |
| DROID VR（含视频） | ~600-1000 MB | 60-100 GB | 600-1000 GB |

---

## 选择决策树

```
启动采集项目
    │
    ├─ 有 VR 头盔？
    │   ├─ 否 → 用 Teach-Replay
    │   └─ 是 → 继续
    │
    ├─ 需要多人采集？
    │   ├─ 是 → DROID VR
    │   └─ 否 → 继续
    │
    ├─ 需要大规模数据（>500 条）？
    │   ├─ 是 → DROID VR
    │   └─ 否 → 继续
    │
    ├─ 任务复杂度高，需要精细控制？
    │   ├─ 是 → Teach-Replay
    │   └─ 否 → 继续
    │
    └─ 推荐混合：
        Teach-Replay（前 50 条）→ DROID VR（中期 400 条）→ 混合（后期调优）
```

---

## 常见问题

**Q: 两种方法采集的数据可以混合吗？**  
A: 可以。数据处理管线（HDF5 转换）对来源不敏感。但要注意数据分布差异（VR vs 手动可能有风格偏差）。

**Q: Teach-Replay 采集后可以用 VR 增强吗？**  
A: 可以。Teach-Replay 的轨迹是标准 NPZ 格式，可以作为 DROID 的初始参考。

**Q: 哪个方法适合实时在线学习？**  
A: DROID VR 更适合（高速采集）。Teach-Replay 更适合离线批处理。

**Q: 能否两个方法并行运行？**  
A: 不推荐（资源冲突）。建议串行：先采集一批，再换方法采集。

**Q: 数据质量：哪个更好？**  
A: 平分。Teach-Replay 精度高但变动大；DROID VR 重复性好但映射有偏差。取决于任务。

---

## 推荐工作流（最佳实践）

### 第一天（Teach-Replay，熟悉）

```
09:00 - 启动系统 + 做 3 条 practice 轨迹
09:30 - 采集 15 条真实数据
10:30 - 审查数据，调整采集策略
11:00 - 再采集 15 条
12:00 - 结束
产出：30 条演示 + 数据质量反馈
```

### 第二周（DROID VR，扩展）

```
Day 1-2: 学习 VR 操作（10 条 practice）
Day 3-5: 高效采集
  - Day 3: 100 条
  - Day 4: 150 条
  - Day 5: 150 条
产出：400 条演示 + 高质量视频

总累计：430 条演示
```

### 第三周（混合调优）

```
使用已训练的模型识别错误样本
- 模型失败的场景 → 用 Teach-Replay 采集 50-100 条针对性数据
- 低置信度区域 → 用 VR 采集多样化演示
产出：50-100 条高价值演示

最终数据集：~500 条高质量演示
```

---

## 结论

| 用途 | 推荐 | 理由 |
|------|------|------|
| 初期原型验证 | 🟢 **Teach-Replay** | 快速上手，成本低 |
| 生产级大规模 | 🟢 **DROID VR** | 速度快，质量稳定 |
| 质量优化微调 | 🟢 **Teach-Replay** | 精确控制，高精度 |
| 长期维护 | 🟢 **混合** | 各取所长，互补 |

**最终建议：** 从 Teach-Replay 开始（学习曲线平缓），后期切换或混用 DROID VR（提升效率）。

