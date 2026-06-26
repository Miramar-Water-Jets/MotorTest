# Use the Dusty NV Humble Base Image for JetPack 4.6.1 (Bionic)
FROM dustynv/ros:humble-ros-base-l4t-r32.7.1

# Disable prompt during package installation
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install system-level dependencies
#    ros2.list is removed to prevent apt-get update failures: there are no official
#    ROS 2 Humble apt packages for Ubuntu 18.04 Bionic, so that source causes errors.
#    gcc-8/g++-8: GCC 7 (the Ubuntu 18.04 default) has a bug where it cannot implicitly
#    convert std::variant<...> to std::optional<std::variant<...>> when the variant type
#    is sufficiently complex. This bug is triggered by rclcpp/client.hpp when compiling
#    the mavros home_position plugin. GCC 8 ships in the standard Bionic repos and
#    has a fixed std::optional implementation.
RUN rm -f /etc/apt/sources.list.d/ros2.list \
    && apt-get update && apt-get install -y \
    python3-pip \
    python3-vcstool \
    build-essential \
    cmake \
    git \
    wget \
    libasio-dev \
    libeigen3-dev \
    libtinyxml2-dev \
    libconsole-bridge-dev \
    libgeographic-dev \
    geographiclib-tools \
    gcc-8 \
    g++-8 \
    && rm -rf /var/lib/apt/lists/*

# GCC 8 is stricter than GCC 7: std::ios::streamoff is non-standard (only
# std::streamoff is in the C++ standard). The system GeographicLib headers on
# Bionic (installed above via libgeographic-dev) use the non-standard form,
# which fails to compile under GCC 8. Patch it in-place.
RUN find /usr/include/GeographicLib -name "*.hpp" \
    -exec sed -i 's/std::ios::streamoff/std::streamoff/g' {} +

# 2. Install Python build tools via pip3
#    - colcon-common-extensions: not in Ubuntu 18.04 apt repos (only in ROS 2 apt repo)
#    - empy must be <4.x: ROS 2 message generators use "import em" which was renamed
#      in empy 4.0, breaking all code generation if a newer version is installed
RUN pip3 install \
    "empy<4" \
    colcon-common-extensions \
    future \
    transforms3d

# 3. Install GeographicLib datasets (Mandatory for MAVROS)
RUN wget https://raw.githubusercontent.com/mavlink/mavros/ros2/mavros/scripts/install_geographiclib_datasets.sh \
    && chmod +x install_geographiclib_datasets.sh \
    && ./install_geographiclib_datasets.sh \
    && rm install_geographiclib_datasets.sh

# 4. Setup the ROS 2 Workspace
WORKDIR /workspace/mavros_ws
RUN mkdir -p src

# 5. Fetch MAVLink, MAVROS, and geographic_info from the correct ROS 2 sources
#    - mavlink: must come from ros2-gbp/mavlink-gbp-release at branch release/humble/mavlink.
#      The main mavlink/mavlink.git repo is the bare C library (no package.xml) and
#      cannot be built as a ROS package. The correct repo/branch is confirmed in the
#      official ROS 2 Humble rosdistro index.
#      PINNED to tag 2022.12.30-1 (commit 36e0f9e): the release/humble/mavlink branch HEAD
#      is now mavlink 2026.3.3, in which MAV_PROTOCOL_CAPABILITY was moved from common.xml
#      to standard.xml. The mavgen C++11 generator puts enums in the namespace of the
#      dialect that DEFINES them, so post-move it lives in mavlink::standard, not
#      mavlink::common. mavros 2.4.0 uses mavlink::common::MAV_PROTOCOL_CAPABILITY, so
#      we must stay on the 2022.12.30 version where it is still in common.xml.
#    - mavros: pinned to 2.4.0 (commit 10569e626a36, Dec 2022). Later commits introduce
#      std::jthread and std::chrono::sys_days which are C++20-only and do not compile
#      under GCC 7 (Ubuntu 18.04). At 2.4.0 the code is C++17-compatible. The tools/
#      directory (which adds the mavros_tools_cpp bare-cmake package requiring C++20)
#      also does not exist at this commit.
#    - geographic_info: ros2 branch provides geographic_msgs and geodesy for ROS 2
#    - angles: ros2 branch; required by geodesy (geographic_info) but absent from the
#      minimal dustynv base image
#    - eigen_stl_containers: required by mavros and mavros_extras; absent from dustynv
#      base image. Source: ros/eigen_stl_containers.git -b ros2 (rosdistro confirmed)
#    - diagnostic_updater: required by mavros and mavros_extras; absent from dustynv
#      base image (diagnostic_msgs IS present, but not the updater library).
#      Lives in ros/diagnostics.git -b ros2-humble (rosdistro confirmed)
RUN git clone https://github.com/ros2-gbp/mavlink-gbp-release.git \
        -b release/humble/mavlink/2022.12.30-1 src/mavlink \
    && git clone https://github.com/mavlink/mavros.git \
        src/mavros && git -C src/mavros checkout 10569e626a36 \
    && git clone https://github.com/ros-geographic-info/geographic_info.git \
        -b ros2 src/geographic_info \
    && git clone https://github.com/ros/angles.git \
        -b humble-devel src/angles \
    && git clone https://github.com/ros/eigen_stl_containers.git \
        -b ros2 src/eigen_stl_containers \
    && git clone https://github.com/ros/diagnostics.git \
        -b ros2-humble src/diagnostics

# 6. Build the dependency packages first so they can be cached separately from
#    the packages that live in this repository.
#    --packages-up-to mavros mavros_extras: only build packages in the dependency
#    chain of our targets. The diagnostics repo contains packages we don't need
#    (diagnostic_aggregator, self_test, etc.) that fail on GCC 7; this flag skips them.
#    CC/CXX=gcc-8/g++-8: Use GCC 8 instead of the system default GCC 7. GCC 7 has a
#    bug where it cannot implicitly convert std::variant<...> to std::optional<std::variant<...>>
#    for complex types, which is triggered by rclcpp/client.hpp in the mavros plugins.
#    -DCMAKE_CXX_STANDARD=17: libmavconn/mavros CMakeLists.txt set C++20 inside an
#    if(NOT CMAKE_CXX_STANDARD) guard, so this override skips that block entirely,
#    making them compile with C++17 under GCC 8.
RUN /bin/bash -c "source /opt/ros/humble/install/setup.bash \
    && CC=gcc-8 CXX=g++-8 colcon build --symlink-install \
        --packages-up-to mavros mavros_extras \
        --executor sequential --parallel-workers 1 \
        --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17"

# 7. Copy the repository packages into the workspace and build them in a separate
#    step so changes to our packages don't invalidate the dependency build cache.
COPY auv_vision /workspace/mavros_ws/src/auv_vision
COPY launching /workspace/mavros_ws/src/launching
COPY pixhawk_packages /workspace/mavros_ws/src/pixhawk_packages
COPY testing_stuff /workspace/mavros_ws/src/testing_stuff

RUN /bin/bash -c "source /opt/ros/humble/install/setup.bash \
    && CC=gcc-8 CXX=g++-8 colcon build --symlink-install \
        --packages-up-to auv_vision launching pixhawk_packages testing_stuff \
        --executor sequential --parallel-workers 1 \
        --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17"

# 8. Auto-source the new workspace on container start
RUN echo "source /workspace/mavros_ws/install/setup.bash" >> ~/.bashrc

# Set default entrypoint behavior
CMD ["bash"]
