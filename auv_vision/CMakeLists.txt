cmake_minimum_required(VERSION 3.8)
project(auv_vision)

# ── Silence CMP0146 (FindCUDA removed in CMake 3.28+) ────────────────────────
# The OpenCV config and cv_bridge ament export both pull in FindCUDA.
# Declaring the policy before any find_package suppresses the warning.
if(POLICY CMP0146)
  cmake_policy(SET CMP0146 OLD)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── ROS dependencies ──────────────────────────────────────────────────────────
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(image_transport REQUIRED)

# ── OpenCV ────────────────────────────────────────────────────────────────────
find_package(OpenCV REQUIRED)

# ── CUDA (legacy FindCUDA — available on JetPack / L4T) ──────────────────────
find_package(CUDA REQUIRED)

# ── TensorRT ─────────────────────────────────────────────────────────────────
# Search paths cover x86_64, aarch64 (Jetson/JetPack), and custom installs.
find_path(TENSORRT_INCLUDE_DIR NvInfer.h
  HINTS
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    /usr/include/aarch64-linux-gnu
    /usr/include/x86_64-linux-gnu
    /usr/local/cuda/include
    /usr/local/tensorrt/include
    /opt/tensorrt/include
  DOC "TensorRT include directory"
)

find_library(TENSORRT_LIB nvinfer
  HINTS
    /usr/lib/aarch64-linux-gnu
    /usr/lib/x86_64-linux-gnu
    /usr/local/cuda/lib64
    /usr/local/tensorrt/lib
    /opt/tensorrt/lib
  DOC "TensorRT nvinfer library"
)

find_library(TENSORRT_PLUGIN_LIB nvinfer_plugin
  HINTS
    /usr/lib/aarch64-linux-gnu
    /usr/lib/x86_64-linux-gnu
    /usr/local/cuda/lib64
    /usr/local/tensorrt/lib
    /opt/tensorrt/lib
  DOC "TensorRT nvinfer_plugin library"
)

if(NOT TENSORRT_INCLUDE_DIR)
  message(FATAL_ERROR
    "TensorRT headers (NvInfer.h) not found. "
    "Install TensorRT or set -DTENSORRT_INCLUDE_DIR=<path>")
endif()
if(NOT TENSORRT_LIB)
  message(FATAL_ERROR
    "TensorRT library (libnvinfer) not found. "
    "Install TensorRT or set -DTENSORRT_LIB=<path>")
endif()

message(STATUS "TensorRT include: ${TENSORRT_INCLUDE_DIR}")
message(STATUS "TensorRT lib:     ${TENSORRT_LIB}")
message(STATUS "TensorRT plugin:  ${TENSORRT_PLUGIN_LIB}")
message(STATUS "CUDA includes:    ${CUDA_INCLUDE_DIRS}")
message(STATUS "CUDA libs:        ${CUDA_LIBRARIES}")

# ── camera_node ───────────────────────────────────────────────────────────────
add_executable(camera_node src/camera_node.cpp)

target_include_directories(camera_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${OpenCV_INCLUDE_DIRS}
)

ament_target_dependencies(camera_node
  rclcpp
  sensor_msgs
  cv_bridge
  image_transport
)

target_link_libraries(camera_node
  ${OpenCV_LIBS}
)

# ── detection_node ────────────────────────────────────────────────────────────
add_executable(detection_node src/detection_node.cpp)

target_include_directories(detection_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${OpenCV_INCLUDE_DIRS}
  ${CUDA_INCLUDE_DIRS}
  ${TENSORRT_INCLUDE_DIR}
)

ament_target_dependencies(detection_node
  rclcpp
  sensor_msgs
  std_msgs
  cv_bridge
  image_transport
)

target_link_libraries(detection_node
  ${OpenCV_LIBS}
  ${CUDA_LIBRARIES}
  ${TENSORRT_LIB}
  ${TENSORRT_PLUGIN_LIB}
)

# ── install ───────────────────────────────────────────────────────────────────
install(TARGETS
  camera_node
  detection_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()

