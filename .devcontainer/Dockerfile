# Dev container image based on a normal ROS 2 Humble desktop image.
# This image installs the repository's runtime dependencies from apt/rosdep
# but does NOT build the repository itself (the workspace is bind-mounted
# by the devcontainer and built locally).
FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive

# 1. Install core build/runtime tools and the repository's ROS dependencies
#    from apt instead of building them from source.
RUN apt-get update && apt-get install -y \
    # Build/development tools
    build-essential \
    cmake \
    git \
    curl \
    wget \
    ca-certificates \
    pkg-config \
    libopencv-dev \
    clang \
    libclang \
    libclang-dev \
    python3-pip \
    python3-vcstool \
    ros-dev-tools \
    # ROS 2 Humble packages used by this repo
    ros-humble-desktop \
    ros-humble-mavros \
    ros-humble-mavros-msgs \
    ros-humble-launch \
    ros-humble-launch-ros \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-tf-transformations \
    # Python packages used by nodes
    python3-colcon-common-extensions \
    python3-empy \
    python3-transforms3d \
    python3-opencv \
    # GeographicLib datasets for MAVROS
    geographiclib-tools \
    && rm -rf /var/lib/apt/lists/*

# 2. Install the GeographicLib datasets required by MAVROS at runtime.
RUN wget https://raw.githubusercontent.com/mavlink/mavros/ros2/mavros/scripts/install_geographiclib_datasets.sh \
    && chmod +x install_geographiclib_datasets.sh \
    && ./install_geographiclib_datasets.sh \
    && rm install_geographiclib_datasets.sh

ENV RUSTUP_HOME=/opt/rust/rustup
ENV CARGO_HOME=/opt/rust/cargo
ENV PATH=/opt/rust/cargo/bin:${PATH}

# 3. Install Rust.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable

# 4. Create the workspace directory. The devcontainer will bind-mount the
#    repository into /workspace/mavros_ws/src/MotorTest.
WORKDIR /workspace/mavros_ws
RUN mkdir -p src

# 5. Source ROS automatically in interactive shells.
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc

CMD ["bash"]
