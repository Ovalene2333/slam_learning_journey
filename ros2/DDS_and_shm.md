# DDS\_and\_shm

## DDS

DDS (Data Distribution Service，数据分发服务) 是由 OMG (Object Management Group) 维护的一个开放的国际标准。它是一种以“数据为中心” (Data-Centric) 的发布/订阅 (Publish-Subscribe) 中间件协议，专为分布式、实时和高可靠性的系统设计。

在ROS2中，DDS是其核心通信机制的基石。ROS2通过一个称为 RMW (ROS Middleware Interface) 的抽象层来与底层的DDS实现进行交互。这种设计使得ROS2具有很强的灵活性，用户可以根据需求切换不同的DDS供应商，例如：

  * Eclipse Cyclone DDS (ROS2 Humble的默认选项之一)
  * eProsima Fast DDS (ROS2 Foxy, Galactic的默认选项)
  * RTI Connext DDS

DDS的核心特性包括：

1.  **数据为中心**：通信的焦点是“数据”本身（通过Topic来定义），而不是发送或接收数据的节点。
2.  **动态发现**：节点（发布者和订阅者）在网络中可以自动发现彼此，无需集中的主节点（Master）。
3.  **QoS (Quality of Service)**：DDS提供了极其丰富的服务质量策略，允许开发者精细控制通信的可靠性 (Reliability)、持久性 (Durability)、延迟 (Latency) 等。

DDS负责底层的实际数据传输。根据配置和实现的不同，DDS可以使用多种传输方式，如UDP（默认，支持多播）、TCP，以及本文档将重点介绍的共享内存（Shared Memory, SHM），以实现在同一台机器上的高性能通信。

## ROS2高速通信-共享内存

在ROS2中，节点（Node）之间的数据通信是整个系统运行的核心。对于需要处理大量数据（如图像、点云、雷达数据）的机器人应用，标准的网络通信方式（如TCP/UDP）可能会因为内存拷贝和数据序列化/反序列化而成为性能瓶颈。为了解决这个问题，ROS2引入了共享内存（Shared Memory）通信机制，允许在同一台物理主机上的不同进程直接访问同一块内存区域，从而实现“零拷贝”（Zero-Copy）的数据传输，极大地提升了通信效率。

本文档将详细介绍如何在ROS2中配置和使用共享内存进行高速通信。

### 共享内存的基本原理

共享内存是进程间通信（IPC, Inter-Process Communication）最快的方式之一。其核心思想是，由一个进程在内存中创建一个“共享区域”，其他进程可以将这个区域“挂载”到自己的地址空间中。这样一来，任何一个进程对这块内存的修改，其他进程都能立刻“看到”，而无需进行数据的复制。

在ROS2的生态中，共享内存通信通常是借助底层的DDS（Data Distribution Service）中间件实现的。目前，主流的支持共享内存的DDS实现是 **Eclipse Cyclone DDS**，它通过集成 **Eclipse iceoryx** 项目来提供零拷贝的共享内存传输能力。

当启用共享内存后，ROS2的通信流程会发生如下变化：

  * **发布者（Publisher）**：当发布一个大的数据消息时，发布者会从iceoryx管理的共享内存池中申请一块内存，将数据直接填充到这块内存中，然后发布一个指向该内存地址的“指针”或引用。
  * **订阅者（Subscriber）**：订阅者接收到这个“指针”后，直接通过该指针访问共享内存中的数据，无需将数据从网络堆栈或操作系统的内核空间拷贝到用户空间。

这种方式避免了至少两次数据拷贝（发送端的用户空间到内核空间，接收端的内核空间到用户空间），显著降低了延迟，并减少了CPU的负载。

### 系统要求与环境准备

在开始之前，请确保你的系统满足以下要求：

  * **操作系统**：Linux (目前共享内存功能在Linux上的支持最为完善和稳定)。
  * **ROS2版本**：ROS2 Foxy Fitzroy及之后的版本（建议使用Galactic、Humble或更新版本，因为其对共享内存的支持更为成熟）。
  * **DDS中间件**：`rmw_cyclonedds_cpp`。这是默认与Cyclone DDS集成的RMW（ROS Middleware）层。请确保已经安装了ROS2的`ros-<distro>-rmw-cyclonedds-cpp`包。

<!-- end list -->

```bash
sudo apt install ros-humble-rmw-cyclonedds-cpp
sudo apt install iceoryx
```

你可以通过以下命令检查当前ROS2环境默认的RMW实现：

```bash
echo $RMW_IMPLEMENTATION
```

如果输出为空或不是`rmw_cyclonedds_cpp`，你可以在运行ROS2节点前手动指定它。

建议查看`iceoryx`的对应工具的版本:

```bash
iox-roudi --version && iox-introspection-client --version
```

> 这里有可能遇到版本不一样的情况，可以使用`which cmd`来搞清楚到底是哪一个。需要注意的是必须使用`/opt/ros/<ros_distro>`下的那一个。

### 启用Cyclone DDS的共享内存功能

启用共享内存功能主要分为两个步骤：**启动iceoryx守护进程** 和 **配置Cyclone DDS**。

#### 启动iceoryx路由守护进程 (RouDi)

iceoryx使用一个名为`RouDi`的守护进程来管理和协调共享内存段的分配。在运行任何使用共享内存的ROS2节点之前，必须先启动`iox-roudi`。

打开一个新的终端，然后执行：

```bash
iox-roudi # 一般在ros的目录如`/opt/ros/humble/bin/iox-roudi`下
# 这个版本和ros使用的版本是匹配的
```

这个进程需要在后台持续运行。如果你的系统中找不到`iox-roudi`命令，请确认你是否完整安装了ROS2桌面版（通常会包含iceoryx）。如果手动安装，一定需要安装和对应ros2版本匹配的iceoryx.

#### 创建Cyclone DDS配置文件

为了让ROS2节点知道要使用共享内存，你需要创建一个XML配置文件来显式地启用该功能。

创建一个名为`cyclonedds.xml`的文件，内容如下：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config">
  <Domain id="any">
    <SharedMemory>
        <Enable>true</Enable>
        <LogLevel>info</LogLevel>
    </SharedMemory>
  </Domain>
</CycloneDDS>
```

```bash
# 或者直接写入，默认在根目录下面
cat > ~/cyclonedds.xml <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config">
  <Domain id="any">
    <SharedMemory>
        <Enable>true</Enable>
        <LogLevel>info</LogLevel>
    </SharedMemory>
  </Domain>
</CycloneDDS>
XML
```

这个配置文件告诉Cyclone DDS在任何域（Domain ID）上都尝试启用共享内存。

#### 设置环境变量并运行节点

现在，你可以通过设置`CYCLONEDDS_URI`环境变量，让你的ROS2节点加载这个配置文件。

1.  **启动 RouDi** (如果还没启动的话):

<!-- end list -->

```bash
# 在第一个终端
iox-roudi
```

2.  **启动发布者节点**：

<!-- end list -->

```bash
# 在第二个终端
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$HOME/cyclonedds.xml"
# 以图像发布为例
ros2 run image_publisher image_publisher_node \
  --ros-args --remap /image_raw:=/image \
            -p publish_rate:=30.0 \
            -p frame_id:=camera_optical_frame \
            -p filename:=/path/to/video
```

3.  **启动订阅者节点**：

其实直接`rqt`，然后启动`image_viewer`就可以进行初步的检查，如果配的有问题直接会报错。

```bash
# 在第三个终端
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$HOME/cyclonedds.xml"
ros2 run image_tools showimage --ros-args --remap image:=/image
```

当发布者和订阅者都通过这个配置启动后，它们之间的通信（如果消息尺寸足够大，值得使用共享内存）就会自动通过iceoryx进行。

#### 可能遇到的问题

如果你传输图像数据，有可能会遇到共享内存块不够大的问题:

```bash
2025-10-06 18:48:33.523 [ Fatal ]: The following mempools are available:  MemPool [ ChunkSize = 168, ChunkPayloadSize = 128, ChunkCount = 10000 ]  MemPool [ ChunkSize = 1064, ChunkPayloadSize = 1024, ChunkCount = 5000 ]  MemPool [ ChunkSize = 16424, ChunkPayloadSize = 16384, ChunkCount = 1000 ]  MemPool [ ChunkSize = 131112, ChunkPayloadSize = 131072, ChunkCount = 200 ]  MemPool [ ChunkSize = 524328, ChunkPayloadSize = 524288, ChunkCount = 50 ]  MemPool [ ChunkSize = 1048616, ChunkPayloadSize = 1048576, ChunkCount = 30 ]  MemPool [ ChunkSize = 4194344, ChunkPayloadSize = 4194304, ChunkCount = 10 ]
Could not find a fitting mempool for a chunk of size 4665756
2025-10-06 18:48:33.523 [Warning]: ICEORYX error! MEPOO__MEMPOOL_GETCHUNK_CHUNK_IS_TOO_LARGE
```

`iceoryx`的默认内存池大小最大为4MB,而在这里的一张图片大小就为4.45MB，因此需要修改配置文件。

创建一个自定义的`my_roudi_config.toml`:

```toml
[general]
version = 1

# 一个共享内存段；如需按访问权限分段，可再添加 [[segment]] 并设置 reader/writer 组
[[segment]]
# 可选：限制读写的用户组（Linux group 名称）
# reader = "foo"
# writer = "bar"

# ---------- Mempools（chunk 载荷大小与数量）----------
# 注意：size 必须是 8 的倍数且 > 8（alignment=8）
[[segment.mempool]]
size  = 128      # 128B 载荷
count = 10000

[[segment.mempool]]
size  = 1024     # 1KB 载荷
count = 5000

[[segment.mempool]]
size  = 16384    # 16KB 载荷
count = 1000

[[segment.mempool]]
size  = 131072   # 128KB 载荷
count = 200

[[segment.mempool]]
size  = 524288   # 512KB 载荷
count = 50

[[segment.mempool]]
size  = 1048576  # 1MB 载荷
count = 30

[[segment.mempool]]
size  = 4194304  # 4MB 载荷
count = 10

[[segment.mempool]]
size  = 8388608  # 添加了 8MB 载荷
count = 10
```

然后运行

```bash
iox-roudi -c ~/my_roudi_config.toml
```

这个时候就不会报错，能够正常运行了。

### 性能优势与适用场景

#### 优势：

  * **极低的延迟**：避免了网络协议栈和数据拷贝的开销。
  * **高吞吐量**：特别适合传输大数据，如高清图像（\>1MB）、点云数据等。
  * **低CPU占用**：数据传输过程中的CPU负载显著降低，可以将计算资源留给更重要的算法。

#### 适用场景：

  * **同一主机内的节点通信**：共享内存仅限于在同一台物理机或虚拟机上的进程间通信。它不能用于跨网络的通信。
  * **大数据传输**：对于小消息（几百字节），使用共享内存带来的优势可能不明显，甚至可能因为额外的管理开销而略微变慢。其威力主要体现在处理大尺寸消息时。
  * **高频率通信**：在需要高频率发布和订阅大量数据的场景下，共享内存可以有效防止消息堆积和延迟。

### 局限性与注意事项

  * **跨容器通信**：默认情况下，Docker容器之间有独立的内存空间，因此标准的共享内存无法直接跨容器工作。需要特殊的Docker配置（如使用`--ipc=host`）才能实现。
  * **QoS（服务质量）策略**：某些QoS设置（例如`Transient Local`的某些历史记录行为）在共享内存模式下的支持可能与默认的UDP传输有所不同。在使用时需要进行充分的测试。
  * **配置复杂性**：相比于ROS2的默认“开箱即用”的通信，使用共享内存需要额外的手动配置步骤。

### 总结

通过利用Eclipse Cyclone DDS和iceoryx，ROS2可以实现高效的共享内存通信，为处理大规模数据的机器人应用提供了强大的性能保障。虽然配置过程需要一些额外的步骤，但其带来的低延迟和高吞吐量优势在许多场景下是物超所值的。当你的ROS2系统在单机内部遇到通信瓶颈时，共享内存无疑是一个值得尝试的优化方案。