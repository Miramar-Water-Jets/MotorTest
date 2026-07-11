cmake_minimum_required(VERSION 3.8)
project(auv_vision)

find_package(ament_cmake REQUIRED)
find_program(CARGO_EXECUTABLE cargo REQUIRED)

set(CARGO_TARGET_DIR "${CMAKE_CURRENT_BINARY_DIR}/cargo-target")
set(VISION_NODE "${CARGO_TARGET_DIR}/release/vision_node")

add_custom_command(
  OUTPUT "${VISION_NODE}"
  COMMAND "${CMAKE_COMMAND}" -E env
    "CARGO_TARGET_DIR=${CARGO_TARGET_DIR}"
    "CPLUS_INCLUDE_PATH=${CMAKE_CURRENT_SOURCE_DIR}/sysroot/include"
    "TENSORRT_LIB_DIR=${CMAKE_CURRENT_SOURCE_DIR}/sysroot/lib"
    "LIBRARY_PATH=${CMAKE_CURRENT_SOURCE_DIR}/sysroot/lib"
    "RUSTFLAGS=-Lnative=${CMAKE_CURRENT_SOURCE_DIR}/sysroot/lib -C link-arg=-Wl,--allow-shlib-undefined"
    "${CARGO_EXECUTABLE}" build --manifest-path "${CMAKE_CURRENT_SOURCE_DIR}/Cargo.toml" --release
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/Cargo.toml"

    "${CMAKE_CURRENT_SOURCE_DIR}/src/main.rs"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tensorrt.rs"
  COMMENT "Building vision_node"
  VERBATIM
)

add_custom_target(vision_node ALL DEPENDS "${VISION_NODE}")

install(PROGRAMS "${VISION_NODE}"
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
