# ROSBAG

## 从ROS1转换

`rosbags` 是纯 Python 库，能直接读取/写入 ROS1/ROS2 的 bag，并在两者之间高效互转，不依赖任何 ROS 发行版。([GitLab][1])

**1）安装**

```bash
sudo apt install python3-pip
pip install rosbags
```

（官方文档说明：`rosbags` 不依赖 ROS 堆栈，并自带 rosbag1/rosbag2 读写与“高效转换器”。）([GitLab][1])

**2）一行命令完成转换**

```bash
# 将 ROS1 的 foo.bag 转成 ROS2（会得到目录 foo/，内部为 rosbag2 存储）
rosbags-convert --src foo.bag

# 指定输出目录（例如输出到 ros2_bag/）
rosbags-convert --src foo.bag --dst ros2_bag
```

## ROS2 BAG的使用（详细）

> 适用于 `ros2 bag`（rosbag2）。以下命令在常见 ROS 2 发行版（Foxy→Humble→Iron 等）下通用；个别选项在早期发行版可能缺失。

### 1）快速了解 & 查看信息

```bash
# 查看 bag 基本信息（存储后端、时长、主题、消息数、起止时间等）
ros2 bag info <bag_dir>
```

典型输出中会包含：

* **storage**（默认 `sqlite3`，也可能是 `mcap` 等）
* **compression**（`zstd`/`lz4` 或 none）
* **duration / start / end / messages**
* **topics**（含每个主题的 QoS 记录）

---

### 2）录制（record）

```bash
# 录制全部主题到当前目录，自动生成名称（bag_YYYY_MM_DD-...）
ros2 bag record -a

# 指定输出名
ros2 bag record -a -o my_bag

# 只录制指定主题
ros2 bag record /camera/image_raw /tf /odom -o nav_cam

# 包含隐藏主题（以“_”开头，或 /rosout 等）
ros2 bag record -a --include-hidden-topics -o with_hidden

# 指定存储后端（如 mcap；系统需已安装对应插件）
ros2 bag record -a -o my_bag --storage mcap

# 压缩（文件级 or 消息级；常见格式 zstd）
ros2 bag record -a -o my_bag --compression-mode file --compression-format zstd

# 分段保存（按大小/时长轮转）
ros2 bag record -a -o split_bag --max-bag-size 1024     # 单段上限 1GB
ros2 bag record -a -o split_bag --max-bag-duration 60   # 单段上限 60s

# 使用 QoS 覆盖文件（订阅侧，用于“录制时”与发布端 QoS 匹配）
ros2 bag record -a -o my_bag --qos-profile-overrides-path qos_record.yaml
```

**示例 QoS 覆盖文件（record/play 通用结构）：`qos_record.yaml`**

```yaml
# 覆盖特定主题的订阅/发布 QoS（常用于解决可靠性/耐久性不匹配导致“录不到/放不出”）
# 可只写需要的条目，未写的主题沿用默认值
topics:
  - topic: /camera/image_raw
    qos:
      reliability: reliable      # reliable | best_effort
      durability: transient_local # transient_local | volatile
      history: keep_last         # keep_last | keep_all
      depth: 10
  - topic: /tf
    qos:
      reliability: best_effort
      durability: volatile
      history: keep_last
      depth: 100
```

> 小贴士
>
> * **录不到消息** 多为 QoS 不匹配：为录制命令加 `--qos-profile-overrides-path`，将订阅侧改成与发布端一致或更宽松。
> * **大图像/高速话题**：优先选择 `mcap` 存储或开启压缩，并适当增大 `depth`。
> * **长时间录制**：务必启用**分段**，方便后期管理与拷贝。

---

### 3）回放（play）

```bash
# 基本回放
ros2 bag play <bag_dir>

# 循环播放、调整速率
ros2 bag play <bag_dir> -l        # loop
ros2 bag play <bag_dir> -r 0.5    # 半速
ros2 bag play <bag_dir> -r 2.0    # 2 倍速

# 仅回放部分主题（白名单）
ros2 bag play <bag_dir> --topics /tf /odom

# 从偏移处开始（跳过最开始的一段）
ros2 bag play <bag_dir> --start-offset 10.0   # 从第 10 秒开始

# 发布 /clock（仿真时常用；让节点用仿真时间）
ros2 bag play <bag_dir> --clock
# 注意需要在其他节点参数中设置：use_sim_time=true

# 在回放侧强制 QoS（解决订阅侧收不到的情况）
ros2 bag play <bag_dir> --qos-profile-overrides-path qos_play.yaml

# 使用特定存储后端读取（当 bag 不是 sqlite3 时）
ros2 bag play <bag_dir> --storage mcap
```

**示例 QoS 覆盖文件（回放侧发布 QoS）：`qos_play.yaml`**

```yaml
topics:
  - topic: /camera/image_raw
    qos:
      reliability: reliable
      durability: volatile        # 通常回放发布用 volatile；除非下游需要 transient_local
      history: keep_last
      depth: 10
  - topic: /tf_static
    qos:
      reliability: reliable
      durability: transient_local # static 变换常见为 transient_local
      history: keep_last
      depth: 1
```

> 小贴士
>
> * 若下游订阅者 QoS 要求“**transient_local**”（尤其 `/tf_static`、某些地图/参数类话题），回放侧也需要相同耐久性，否则对端可能收不到**历史**消息。
> * 使用 `--clock` 时，确保其他节点启用 `use_sim_time`。
> * 回放大量图像时，SSD I/O 会显著影响实时性；必要时降低速率或预解压。

---

### 4）过滤、裁剪与转换

```bash
# 过滤生成新的 bag（按表达式挑选消息；常见做法是按主题或时间窗）
# 表达式语法取决于发行版；最通用办法是直接白名单主题：
ros2 bag filter <src_bag_dir> -o <dst_bag_dir> --topics /odom /tf

# 也可按时间裁剪（部分发行版支持 --start / --duration 等；若无，可通过回放+二次录制实现）
# 方法A：部分版本
ros2 bag filter <src> -o <dst> --start 10.0 --duration 60.0
# 方法B：通用方案（回放窗口+再录）：
#   1) ros2 bag play <src> --start-offset 10 --clock
#   2) 同时 ros2 bag record 你需要的主题，持续 60s 后 Ctrl-C 停止

# 存储后端转换（示例：sqlite3 → mcap 或反向；需具备对应插件）
ros2 bag convert <src_bag_dir> --output <dst_bag_dir> --storage mcap
# 若发行版无 convert 子命令，可用“回放 + 再录制 + 指定 --storage”实现等效转换
```

---

### 5）压缩与解压

```bash
# 对已录制 bag 进行压缩（文件级）
ros2 bag compress <bag_dir> --compression-format zstd --compression-mode file

# 解压
ros2 bag decompress <bag_dir>
```

> **选择模式**
>
> * `file`：整体文件压缩，CPU 开销低，读写快。
> * `message`：逐消息压缩，压缩比常更高，但占用更多 CPU。

---

### 6）索引修复与诊断

```bash
# 目录被意外中断或拷贝损坏时，尝试重建索引
ros2 bag reindex <bag_dir>

# 常见排错思路
# 1) ros2 bag info 查看是否识别到主题/消息数
# 2) 检查 QoS：录制/回放两端是否匹配（reliable/best_effort，durability 等）
# 3) storage 插件是否齐全（mcap/sqlite3）
# 4) 权限/磁盘空间/路径大小写（Linux/Windows）问题
```
