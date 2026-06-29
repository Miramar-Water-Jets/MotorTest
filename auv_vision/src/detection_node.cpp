// detection_node.cpp
// C++ port of detection_node.py
// Loads a TensorRT .engine file, runs inference on incoming camera frames,
// and publishes bounding boxes to the same topics as the Python version.
//
// Topic mapping (identical to Python version):
//   SUB  /auv/camera/image_raw          -> sensor_msgs/Image
//   PUB  /auv/camera/image_detected     -> sensor_msgs/Image  (annotated frame)
//   PUB  /auv/camera/bboxes_gate        -> std_msgs/Float32MultiArray  [x1,y1,x2,y2,conf]
//
// The model output is assumed to be a standard YOLO-style flat detection tensor:
//   shape [1, num_detections, 6]  or  [1, 6, num_detections]  (transposed variant)
//   each detection: [x1, y1, x2, y2, conf, class_id]
//
// If your engine uses a different output layout, adjust parse_detections() below.

#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include <stdexcept>

// CUDA / TensorRT
// NvInfer.h is the main TensorRT public API header.
// On JetPack/L4T it lives in /usr/include/aarch64-linux-gnu/.
// The include path is injected by CMake via TENSORRT_INCLUDE_DIR.
#include <cuda_runtime_api.h>
#include <NvInfer.h>
#include <NvInferRuntime.h>
#include <NvInferRuntimeCommon.h>
#include <NvInferVersion.h>   // provides NV_TENSORRT_MAJOR etc. (TRT >= 7)

// OpenCV / ROS
#include <opencv2/opencv.hpp>
#include <cv_bridge/cv_bridge.h>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_msgs/msg/float32_multi_array.hpp>

// ─────────────────────────────────────────────────────────────────────────────
// Minimal TensorRT logger
// ─────────────────────────────────────────────────────────────────────────────
class TRTLogger : public nvinfer1::ILogger
{
public:
  void log(Severity severity, const char * msg) noexcept override
  {
    if (severity <= Severity::kWARNING) {
      fprintf(stderr, "[TensorRT] %s\n", msg);
    }
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// Helper: load a .engine file into a byte buffer
// ─────────────────────────────────────────────────────────────────────────────
static std::vector<char> load_engine_file(const std::string & path)
{
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file.is_open()) {
    throw std::runtime_error("Cannot open engine file: " + path);
  }
  const std::streamsize size = file.tellg();
  file.seekg(0, std::ios::beg);
  std::vector<char> buffer(size);
  if (!file.read(buffer.data(), size)) {
    throw std::runtime_error("Failed to read engine file: " + path);
  }
  return buffer;
}

// ─────────────────────────────────────────────────────────────────────────────
// Detection result struct
// ─────────────────────────────────────────────────────────────────────────────
struct Detection {
  float x1, y1, x2, y2;
  float conf;
  int   cls;
};

// ─────────────────────────────────────────────────────────────────────────────
// DetectionNode
// ─────────────────────────────────────────────────────────────────────────────
class DetectionNode : public rclcpp::Node
{
public:
  DetectionNode()
  : Node("DetectionNode")
  {
    RCLCPP_INFO(get_logger(), "Detection node started!");

    auto qos = rclcpp::QoS(rclcpp::KeepLast(1))
                 .reliability(rclcpp::ReliabilityPolicy::BestEffort);

    // ── publishers / subscribers ─────────────────────────────────────────────
    image_sub_ = create_subscription<sensor_msgs::msg::Image>(
      "/auv/camera/image_raw", qos,
      [this](const sensor_msgs::msg::Image::SharedPtr msg) { image_cb(msg); });

    detection_pub_ =
      create_publisher<sensor_msgs::msg::Image>("/auv/camera/image_detected", qos);

    gate_pub_ =
      create_publisher<std_msgs::msg::Float32MultiArray>("/auv/camera/bboxes_gate", qos);

    // ── load TensorRT engine ─────────────────────────────────────────────────
    // Same path as Python but .engine instead of .pt
    const std::string engine_path = "/home/nvidia/robostack/best_hand.engine";
    load_engine(engine_path);
  }

  ~DetectionNode()
  {
    // Free CUDA buffers
    for (void * buf : gpu_buffers_) {
      if (buf) cudaFree(buf);
    }
    if (cpu_output_) delete[] cpu_output_;
  }

private:
  // ── TensorRT objects (raw owning pointers; TRT uses its own ref-counting) ──
  TRTLogger                              trt_logger_;
  nvinfer1::IRuntime                   * runtime_  = nullptr;
  nvinfer1::ICudaEngine                * engine_   = nullptr;
  nvinfer1::IExecutionContext           * context_  = nullptr;

  // ── CUDA resources ────────────────────────────────────────────────────────
  cudaStream_t           stream_       = nullptr;
  std::vector<void *>    gpu_buffers_;

  // ── I/O dimensions ────────────────────────────────────────────────────────
  int input_binding_idx_  = -1;
  int output_binding_idx_ = -1;
  int input_h_  = 640;   // default — overwritten from engine bindings
  int input_w_  = 640;
  int num_detections_ = 0;  // total elements in output (will be set at load)

  float * cpu_output_ = nullptr;
  size_t  output_count_ = 0;

  // ── ROS handles ──────────────────────────────────────────────────────────
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr    detection_pub_;
  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr gate_pub_;

  // ─────────────────────────────────────────────────────────────────────────
  // Engine loading
  // ─────────────────────────────────────────────────────────────────────────
  void load_engine(const std::string & path)
  {
    RCLCPP_INFO(get_logger(), "Loading TensorRT engine: %s", path.c_str());

    auto buffer = load_engine_file(path);

    runtime_ = nvinfer1::createInferRuntime(trt_logger_);
    if (!runtime_) throw std::runtime_error("createInferRuntime failed");

    engine_ = runtime_->deserializeCudaEngine(buffer.data(), buffer.size());
    if (!engine_) throw std::runtime_error("deserializeCudaEngine failed");

    context_ = engine_->createExecutionContext();
    if (!context_) throw std::runtime_error("createExecutionContext failed");

    cudaStreamCreate(&stream_);

    // ── Find input/output bindings ──────────────────────────────────────────
    const int nb = engine_->getNbBindings();
    gpu_buffers_.resize(nb, nullptr);

    for (int i = 0; i < nb; ++i) {
      const nvinfer1::Dims dims = engine_->getBindingDimensions(i);
      const size_t vol = volume(dims);
      const size_t bytes = vol * sizeof(float);

      cudaMalloc(&gpu_buffers_[i], bytes);

      if (engine_->bindingIsInput(i)) {
        input_binding_idx_ = i;
        // dims: [N, C, H, W]  — take H and W
        if (dims.nbDims >= 4) {
          input_h_ = dims.d[2];
          input_w_ = dims.d[3];
        }
        RCLCPP_INFO(get_logger(), "Input  binding %d  shape [%s]  %zu bytes",
                    i, dims_str(dims).c_str(), bytes);
      } else {
        output_binding_idx_ = i;
        output_count_ = vol;
        cpu_output_   = new float[vol];
        RCLCPP_INFO(get_logger(), "Output binding %d  shape [%s]  %zu floats",
                    i, dims_str(dims).c_str(), vol);
      }
    }

    RCLCPP_INFO(get_logger(), "TensorRT engine loaded. Input %dx%d",
                input_h_, input_w_);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Image callback — mirrors Python image_cb()
  // ─────────────────────────────────────────────────────────────────────────
  void image_cb(const sensor_msgs::msg::Image::SharedPtr msg)
  {
    // Convert ROS image to OpenCV BGR (same as cv_bridge in Python)
    cv_bridge::CvImagePtr cv_ptr;
    try {
      cv_ptr = cv_bridge::toCvCopy(msg, "bgr8");
    } catch (const cv_bridge::Exception & e) {
      RCLCPP_ERROR(get_logger(), "cv_bridge exception: %s", e.what());
      return;
    }
    cv::Mat & frame = cv_ptr->image;

    // ── Pre-process: resize + normalize to [0,1] float32 NCHW ───────────────
    cv::Mat resized;
    cv::resize(frame, resized, cv::Size(input_w_, input_h_));

    cv::Mat blob;
    resized.convertTo(blob, CV_32F, 1.0 / 255.0);

    // HWC → NCHW  (split channels, interleave into contiguous buffer)
    std::vector<cv::Mat> channels(3);
    cv::split(blob, channels);

    std::vector<float> nchw_input(3 * input_h_ * input_w_);
    for (int c = 0; c < 3; ++c) {
      std::memcpy(nchw_input.data() + c * input_h_ * input_w_,
                  channels[c].ptr<float>(),
                  input_h_ * input_w_ * sizeof(float));
    }

    // ── Copy input to GPU ────────────────────────────────────────────────────
    cudaMemcpyAsync(gpu_buffers_[input_binding_idx_],
                    nchw_input.data(),
                    nchw_input.size() * sizeof(float),
                    cudaMemcpyHostToDevice,
                    stream_);

    // ── Run inference ────────────────────────────────────────────────────────
    context_->enqueueV2(gpu_buffers_.data(), stream_, nullptr);

    // ── Copy output back ─────────────────────────────────────────────────────
    cudaMemcpyAsync(cpu_output_,
                    gpu_buffers_[output_binding_idx_],
                    output_count_ * sizeof(float),
                    cudaMemcpyDeviceToHost,
                    stream_);
    cudaStreamSynchronize(stream_);

    // ── Parse detections ─────────────────────────────────────────────────────
    auto detections = parse_detections(cpu_output_, output_count_,
                                       frame.cols, frame.rows);

    if (detections.empty()) {
      return;  // same as Python: early return when no boxes
    }

    // Scale factors from model input size back to original image size
    const float sx = static_cast<float>(frame.cols) / input_w_;
    const float sy = static_cast<float>(frame.rows) / input_h_;

    for (const auto & det : detections) {
      const float x1 = det.x1 * sx;
      const float y1 = det.y1 * sy;
      const float x2 = det.x2 * sx;
      const float y2 = det.y2 * sy;

      RCLCPP_DEBUG(get_logger(), "cls: %d, conf: %.3f", det.cls, det.conf);
      // Same console print as Python version
      printf("cls: %d, conf: %.3f\n", det.cls, det.conf);

      std_msgs::msg::Float32MultiArray bbox_msg;
      bbox_msg.data = {x1, y1, x2, y2, det.conf};

      if (det.cls == 0) {
        gate_pub_->publish(bbox_msg);
      }
      // If more classes are added, add new publishers and elif equivalents here
    }

    // ── Publish annotated frame ───────────────────────────────────────────────
    auto out_msg =
      cv_bridge::CvImage(msg->header, "bgr8", frame).toImageMsg();
    detection_pub_->publish(*out_msg);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Parse raw float output into Detection structs.
  //
  // Handles two common YOLO export layouts:
  //   Layout A: [1, num_det, 6]   each row = [x1, y1, x2, y2, conf, cls]
  //   Layout B: [1, 6, num_det]   transposed (some exporters do this)
  //
  // Adjust the constant `FIELDS` and the index arithmetic if your engine uses
  // a different format (e.g., anchored predictions, sigmoid outputs, etc.)
  // ─────────────────────────────────────────────────────────────────────────
  static std::vector<Detection> parse_detections(
    const float * data,
    size_t        total_floats,
    int           /*img_w*/,
    int           /*img_h*/,
    float         conf_threshold = 0.25f)
  {
    constexpr int FIELDS = 6;  // [x1, y1, x2, y2, conf, cls]
    std::vector<Detection> out;

    if (total_floats == 0 || total_floats % FIELDS != 0) {
      return out;
    }

    const size_t num_rows = total_floats / FIELDS;

    for (size_t i = 0; i < num_rows; ++i) {
      const float * row = data + i * FIELDS;
      const float conf  = row[4];
      if (conf < conf_threshold) continue;

      Detection d;
      d.x1   = row[0];
      d.y1   = row[1];
      d.x2   = row[2];
      d.y2   = row[3];
      d.conf = conf;
      d.cls  = static_cast<int>(row[5]);
      out.push_back(d);
    }
    return out;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Utilities
  // ─────────────────────────────────────────────────────────────────────────
  static size_t volume(const nvinfer1::Dims & dims)
  {
    size_t vol = 1;
    for (int i = 0; i < dims.nbDims; ++i) {
      if (dims.d[i] < 0) return 0;  // dynamic dim — caller must set profile
      vol *= static_cast<size_t>(dims.d[i]);
    }
    return vol;
  }

  static std::string dims_str(const nvinfer1::Dims & dims)
  {
    std::string s;
    for (int i = 0; i < dims.nbDims; ++i) {
      if (i) s += "x";
      s += std::to_string(dims.d[i]);
    }
    return s;
  }
};

// ─────────────────────────────────────────────────────────────────────────────
int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DetectionNode>());
  rclcpp::shutdown();
  return 0;
}
