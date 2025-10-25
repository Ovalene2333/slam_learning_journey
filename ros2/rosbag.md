# ROSBAG 教程

## `rosbags`: 轻松实现 ROS1 与 ROS2 的 bag 互转

在 ROS 1 和 ROS 2 共存的环境中，我们经常需要转换 bag 文件格式。`rosbags` 是一个强大的纯 Python 库，它不依赖任何 ROS 发行版，就能直接读取、写入 ROS1 和 ROS2 的 bag，并高效互转。

**1）安装**

```bash
sudo apt install python3-pip
pip install rosbags
```

**2）一行命令完成转换**

```bash
# 示例：从 ROS1 .bag 转换为 ROS2 目录
rosbags-convert --src foo.bag --dst ros2_bag_directory
```
> 注意,如果要把rosbag2转换回rosbag,只支持ros内置的msg不支持自定义msg

## ROS2 BAG 核心用法 (ros2 bag)

本教程将重点介绍 ROS 2 官方工具 `ros2 bag` (rosbag2) 的核心用法。以下命令在 Foxy, Humble, Iron 等主流 ROS 2 发行版中通用（个别高级选项可能在早期版本中缺失）。

-----

### 1）快速了解：查看 Bag 信息

在处理一个未知的 bag 文件时，第一步总是查看它的基本信息。

```bash
ros2 bag info <bag_dir>
```

`info` 命令会显示 bag 的关键元数据，帮助你快速了解内容：

  * **storage**：存储后端（默认 `sqlite3`，高性能 `mcap` 等）
  * **compression**：压缩格式（`zstd`/`lz4` 或 none）
  * **duration / start / end / messages**：时长、起止时间、总消息数
  * **topics**：包含的主题列表、消息类型及各自的 QoS 配置

-----

### 2）录制 (record)

录制是 `ros2 bag` 最核心的功能。

#### 基础录制

```bash
# 录制全部主题到当前目录，自动生成名称（格式如 bag_YYYY_MM_DD-...）
ros2 bag record -a

# 指定输出目录名
ros2 bag record -a -o my_bag

# 只录制指定的主题
ros2 bag record /camera/image_raw /tf /odom -o nav_cam
```

#### 进阶与性能选项

```bash
# 包含隐藏主题（以“_”开头，或 /rosout 等）
ros2 bag record -a --include-hidden-topics -o with_hidden

# 指定存储后端（mcap 性能通常优于默认的 sqlite3）
ros2 bag record -a -o my_bag --storage mcap

# 开启压缩（zstd 是推荐格式，file 模式开销较低）
ros2 bag record -a -o my_bag --compression-mode file --compression-format zstd
```

#### 长时间录制 (分段)

对于长时间运行的系统，必须进行分段保存，避免单个文件过大导致难以管理或损坏。

```bash
# 按大小分段（例如每 1GB 一个文件）
ros2 bag record -a -o split_bag --max-bag-size 1024

# 按时长分段（例如每 60 秒一个文件）
ros2 bag record -a -o split_bag --max-bag-duration 60
```

#### 处理 QoS 不匹配

如果录制时发现某些主题录不进数据，通常是 QoS 不兼容。我们可以提供一个 YAML 文件来覆盖录制节点（订阅方）的 QoS 设置。

```bash
# 使用 QoS 覆盖文件进行录制
ros2 bag record -a -o my_bag --qos-profile-overrides-path qos_record.yaml
```

**示例 `qos_record.yaml` (录制/回放通用结构):**

```yaml
# 覆盖特定主题的订阅/发布 QoS
# 未在此处列出的主题将使用默认值
topics:
  - topic: /camera/image_raw
    qos:
      reliability: reliable       # reliable | best_effort
      durability: transient_local # transient_local | volatile
      history: keep_last
      depth: 10
  - topic: /tf
    qos:
      reliability: best_effort
      durability: volatile
      history: keep_last
      depth: 100
```

> **录制小贴士**
>
>   * **录不到消息？** 绝大多数情况是 QoS 不匹配。使用 `--qos-profile-overrides-path`，确保录制节点（订阅者）的 QoS 设置与发布端兼容（或更宽松）。
>   * **大图像/高速话题**：强烈建议使用 `mcap` 存储并开启 `zstd` 压缩，同时可适当增大 `depth`。
>   * **长时间录制**：务必启用分段 (`--max-bag-size` 或 `--max-bag-duration`)。

-----

### 3）回放 (play)

录制完成后，我们使用 `play` 命令来复现数据。

#### 基础回放

```bash
# 基本回放
ros2 bag play <bag_dir>

# 循环播放
ros2 bag play <bag_dir> -l

# 调整速率（0.5 倍速 / 2 倍速）
ros2 bag play <bag_dir> -r 0.5
ros2 bag play <bag_dir> -r 2.0
```

#### 控制回放内容

```bash
# 仅回放指定的主题
ros2 bag play <bag_dir> --topics /tf /odom 

# 从指定时间偏移处开始（例如跳过前 10 秒）
ros2 bag play <bag_dir> --start-offset 10.0 

# 开始时暂停,不至于手忙脚乱
ros2 bag play <bag_dir> --start-pause bag_path
```

#### 仿真时间回放

在仿真或调试时，我们希望节点使用 bag 中的时间戳，而不是系统当前时间。

```bash
# 回放时发布 /clock 主题
ros2 bag play <bag_dir> --clock
```

**重要**：当使用 `--clock` 时，所有其他需要同步的 ROS 节点在启动时都必须设置参数 `use_sim_time:=true`。

#### 回放中的 QoS 与存储

与录制类似，如果下游节点收不到消息，也可能是 QoS 不匹配（尤其是 `durability`）。

```bash
# 在回放侧（发布方）强制 QoS
ros2 bag play <bag_dir> --qos-profile-overrides-path qos_play.yaml

# 当 bag 不是默认的 sqlite3 时，指定存储后端读取
ros2 bag play <bag_dir> --storage mcap
```

**示例 `qos_play.yaml` (回放侧发布 QoS):**

```yaml
topics:
  - topic: /camera/image_raw
    qos:
      reliability: reliable
      durability: volatile       # 回放时通常用 volatile
      history: keep_last
      depth: 10
  - topic: /tf_static
    qos:
      reliability: reliable
      durability: transient_local # tf_static 这类“静态”话题必须用 transient_local
      history: keep_last
      depth: 1
```

> **回放小贴士**
>
>   * 如果下游订阅者（如 Rviz）的 QoS 要求 `transient_local`（常见于 `/tf_static`、地图等话题），回放侧也必须在 QoS 覆盖文件中指定 `durability: transient_local`，否则对方可能收不到这些“历史”消息。
>   * 使用 `--clock` 时，切记检查其他节点是否已启用 `use_sim_time`。

-----

### 4）过滤、裁剪与转换

有时我们需要对原始 bag 进行“瘦身”或转换格式。

```bash
# 过滤生成新的 bag（例如只保留 /odom 和 /tf）
ros2 bag filter <src_bag_dir> -o <dst_bag_dir> --topics /odom /tf

# 存储后端转换（例如：sqlite3 → mcap）
ros2 bag convert <src_bag_dir> --output <dst_bag_dir> --storage mcap
```

**按时间裁剪的技巧**:

如果你的 ROS 发行版 `ros2 bag filter` 不支持 `--start` / `--duration` 等参数，可以使用“回放+重录制”的通用方法实现裁剪：

1.  (终端1) `ros2 bag play <src> --start-offset 10.0` (从第 10 秒开始播放)
2.  (终端2) `ros2 bag record -o <dst> --topics /odom /tf` (立即开始录制需要的主题，在合适的时间 Ctrl-C 停止)

-----

### 5）压缩与解压

如果录制时忘记压缩，可以后续添加压缩；反之亦然。

```bash
# 对已录制的 bag 进行压缩（文件级，zstd 推荐）
ros2 bag compress <bag_dir> --compression-format zstd --compression-mode file

# 解压
ros2 bag decompress <bag_dir>
```

> **压缩模式选择**
>
>   * `file`：整体文件压缩。CPU 开销低，读写快，推荐。
>   * `message`：逐条消息压缩。压缩比可能更高，但 CPU 占用也更高。

-----

### 6）索引修复与诊断

当 bag 文件损坏、拷贝中断或无法读取时，可以尝试重建索引。有时候你录制了log但是突然断电了就有可能遇到这种情况。

```bash
# 尝试重建索引
ros2 bag reindex <bag_dir>
```

**常见排错思路**:

1.  使用 `ros2 bag info` 检查是否能识别到主题/消息数。
2.  **QoS 问题**：检查录制/回放两端的 `reliability` 和 `durability` 是否匹配。
3.  **Storage 问题**：是否缺少 `mcap` (或 `sqlite3`) 插件？
4.  **环境问题**：检查文件权限、磁盘空间、路径拼写等。