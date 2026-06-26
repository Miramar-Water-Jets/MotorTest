#!/bin/bash
set -e

cd "$(dirname "$0")"

# Source the ROS environment
source install/setup.bash

# Set DYLD_LIBRARY_PATH to include the pixi environment lib directory
# This is needed on macOS for ROS libraries to be found during build
export DYLD_LIBRARY_PATH="$(pwd)/.pixi/envs/humble/lib:$DYLD_LIBRARY_PATH"

# Also set PKG_CONFIG_PATH for pkg-config to find ROS libraries
export PKG_CONFIG_PATH="$(pwd)/.pixi/envs/humble/lib/pkgconfig:$PKG_CONFIG_PATH"

# Build the project
cd auv_vision/auv_vision
cargo build "$@"
