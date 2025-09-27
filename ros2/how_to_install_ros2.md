## 使用fishros

```bash
wget http://fishros.com/install -O fishros && . fishros
```

选择安装桌面版(desktop)

### 环境配置

**强烈推荐使用zsh和对应的zsh-autosuggestions**，以减少你输入冗长命令的时间。
可以在`~/.zshrc`中添加这样的命令:
```bash
source /opt/ros/humble/setup.zsh
```

**严禁直接在.zshrc或者.bahsrc中添加source到工作区的命令！**

### 优雅的进行依赖的配置:使用rosdep

rosdep是ROS中用于安装系统依赖项的命令行工具。它通过扫描工作区中所有功能包的`package.xml`文件来确定需要安装的依赖。

#### 1\. 在 `package.xml` 中添加依赖

首先，你需要在你的功能包下的 `package.xml` 文件中声明你的节点所依赖的其他ROS包。这通常通过添加 `<depend>` 标签来完成。例如，如果你的C++节点依赖于`rclcpp` 和 `std_msgs`，你的`package.xml`文件应该包含以下内容：

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>my_package</name>
  <version>0.0.0</version>
  <description>TODO: Package description</description>
  <maintainer email="user@todo.todo">user</maintainer>
  <license>TODO: License declaration</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>rclcpp</depend>
  <depend>std_msgs</depend>

  <!-- 1. APT 包的声明方式 -->
  <depend>libgoogle-glog-dev</depend> 
  <!-- 2. 一些ROS包有自己的键值,自行查询或者询问AI -->
  <!-- tf_transformations对应python3-tf-transformations-->
  <depend>tf_transformations</depend> 


  <test_depend>ament_lint_auto</test_depend>
  <test_depend>ament_lint_common</test_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

这里的 `<depend>rclcpp</depend>` 和 `<depend>std_msgs</depend>` 就是依赖声明。

#### 2\. 初始化rosdep (首次使用)

如果你是第一次使用rosdep，需要先进行初始化。

```bash
sudo rosdep init
rosdep update
```

#### 3\. 安装依赖

在你的工作区根目录下（例如 `~/ros2_ws/`），运行以下命令来安装`src`文件夹下所有功能包的依赖：

```bash
rosdep install -i --from-paths src --rosdistro humble -y
```

命令解析:

  - `-i` 或 `--ignore-src`: 忽略那些已经存在于`src`目录下的源码包，只安装系统缺失的依赖。
  - `--from-paths src`: 指定扫描`package.xml`的起始路径，这里是`src`文件夹。
  - `--rosdistro humble`: 指定你的ROS发行版，这里是`humble`。
  - `-y`: 对所有安装提示自动回答“是”。

执行此命令后，rosdep会自动通过系统的包管理器（如apt）安装所有缺失的依赖项。

### 一些宏

让你的ros2的终端输出包含颜色(warning的黄色和error的红色)，方便你观察节点启动的状态和是否报错

```bash
export RCUTILS_COLORIZED_OUTPUT=1
```
快捷添加:
```bash
echo "export RCUTILS_COLORIZED_OUTPUT=1" >> ~/.zshrc
```
```bash
echo "export RCUTILS_COLORIZED_OUTPUT=1" >> ~/.bashrc
```