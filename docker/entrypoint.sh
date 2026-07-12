#!/usr/bin/env bash
set -e

source /opt/ros/humble/install/setup.bash
source /workspace/mavros_ws/install/setup.bash

exec "$@"
