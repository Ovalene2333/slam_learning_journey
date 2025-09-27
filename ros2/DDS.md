# DDS 在 ROS 2 里的位置

* \*\*DDS（Data Distribution Service）\*\*是 ROS 2 采用的底层通信中间件标准；
* \*\*RMW 层（ROS Middleware Interface）\*\*把 ROS API（rclcpp / rclpy）与具体 DDS 实现解耦。Humble 常见实现有 **Fast DDS**（eProsima）与 **Cyclone DDS**（Eclipse）。
* 你切换实现通常只需设环境变量：`RMW_IMPLEMENTATION=rmw_fastrtps_cpp` 或 `rmw_cyclonedds_cpp`，不改应用层代码。

# DDS 基本概念与 ROS 映射

* **Domain / ROS\_DOMAIN\_ID**：同一域内才会互相发现。`export ROS_DOMAIN_ID=42` 可把不同系统隔离开。
* **Participant**：进程在一个域中的“身份”；
* **Topic**：数据主题，ROS 话题会映射到 DDS Topic（ROS 会做命名空间与类型名到 DDS 的映射）；
* **Publisher / DataWriter** 与 **Subscriber / DataReader**：发布与订阅端；
* **Service / Action**：

  * Service 通过两条 DDS 话题完成请求/响应；
  * Action 由若干话题与两个服务组合（目标、结果、反馈、状态等）。

# 发现与传输

* **发现机制**：基于 DDSI-RTPS（OMG 标准），通过局域网 UDP 组播进行**对等发现**（无中心）。
* **传输**：默认 UDP；不同实现可选**共享内存**（同机零拷贝）与 **TCP/中继/服务器式发现**等扩展，用于跨网段或更低延迟场景。
* **跨网段注意**：纯组播发现通常过不去三层路由；需要配置发现服务器/中继或静态对端。

# QoS（服务质量）是关键

ROS 2 把 DDS QoS 揉进了 API，通过 QoS 组合来匹配不同数据流的需求。常见策略：

* **Reliability**：

  * `BEST_EFFORT`（尽力而为，低延迟，可能丢包；如高频传感器）
  * `RELIABLE`（可靠传输，有重发，适于关键数据）
* **Durability**：

  * `VOLATILE`（不保存历史）
  * `TRANSIENT_LOCAL`（保留最近样本给后加入者；适合低频状态/参数）
* **History & Depth**：保存多少历史样本 `KEEP_LAST(depth)` / `KEEP_ALL`；
* **Deadline / Lifespan / Liveliness**：时序约束与“活性”心跳，便于检测超时或驱动更新频率要求。

> **QoS 必须匹配**：发布者与订阅者的 QoS 不兼容会导致“看不见彼此”或收不到数据（典型：一端可靠、一端尽力而为；或深度不合理）。

### 代码示例

**C++**

```cpp
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
using namespace std::chrono_literals;
int main(int argc, char** argv){
  rclcpp::init(argc, argv);
  auto node = rclcpp::Node::make_shared("talker");
  auto qos = rclcpp::QoS(rclcpp::KeepLast(10))
               .reliable()
               .durability_volatile()
               .deadline(100ms);
  auto pub = node->create_publisher<std_msgs::msg::String>("chatter", qos);
  // ...
  rclcpp::shutdown();
}
```

**Python**

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
qos = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE
)
# node.create_publisher(String, 'chatter', qos)
```

# 序列化与类型

* DDS 使用 **IDL/XTypes** 与 **CDR** 序列化；ROS 2 借助 `rosidl` 为消息生成类型支持（TypeSupport），让 DDS 可识别并传输。
* **Intra-process**（进程内）优化：同进程节点间可绕过序列化、减少拷贝（rclcpp 中 NodeOptions 可开启/默认启用）。

# 安全（可选）

* 基于 **DDS-Security**：认证、访问控制与加密（SROS2 提供密钥库与证书工具链）。启用后，只有受信参与者能加入域并收发相应话题。

# 常用调试/定位手段

* `ros2 topic list / info -v / echo / hz / bw`：看话题、QoS、频率与带宽；
* `ros2 node info`：查看节点端点与 QoS；
* 检查 **域号** 与 **RMW 实现** 环境变量；
* 不通网段时考虑启用**发现服务器/中继**或指定对端；
* QoS 不匹配时先统一 **Reliability / Durability / Depth** 配置。

# 典型配置建议

* **高频传感器（激光/相机）**：`BEST_EFFORT + KEEP_LAST(5~10) + VOLATILE`，尽量降低延迟；
* **控制/状态**：`RELIABLE + KEEP_LAST(10)`；
* **慢速、需要“补历史”的配置/地图**：`TRANSIENT_LOCAL + RELIABLE + 深度较大`；
* **服务/动作**：默认使用 `RELIABLE`；保持请求/响应可靠投递。

# 常见坑

* **QoS 不兼容** → 订阅端收不到数据；
* **跨网段发现失败** → 配置发现服务器或静态对端，或开启允许单播；
* **类型不匹配** → 确保两端消息类型与包版本一致；
* **大消息吞吐瓶颈** → 使用 intra-process、共享内存传输或适当调大发送缓冲与分片参数。
