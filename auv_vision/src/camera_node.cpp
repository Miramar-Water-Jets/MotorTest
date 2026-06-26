// camera_node.cpp
// C++ port of camera_node.py
// Publishes raw camera frames to /auv/camera/image_raw

#include <chrono>
#include <memory>
#include <string>

#include <opencv2/opencv.hpp>
#include <cv_bridge/cv_bridge.h>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>

using namespace std::chrono_literals;

class CameraNode : public rclcpp::Node
{
public:
  CameraNode()
  : Node("CameraNode")
  {
    RCLCPP_INFO(get_logger(), "Camera node started!");

    auto qos = rclcpp::QoS(rclcpp::KeepLast(1))
                 .reliability(rclcpp::ReliabilityPolicy::BestEffort);

    camera_image_pub_ =
      create_publisher<sensor_msgs::msg::Image>("/auv/camera/image_raw", qos);

    cap_ = cv::VideoCapture(0);
    RCLCPP_INFO(get_logger(), "Camera opened: %s",
                cap_.isOpened() ? "true" : "false");

    if (!cap_.isOpened()) {
      RCLCPP_ERROR(get_logger(), "Could not open camera.");
      return;
    }

    // 10 Hz — same as Python's create_timer(0.1, ...)
    timer_ = create_timer(this, get_clock(), 100ms,
                          [this]() { publish_frame(); });
  }

private:
  void publish_frame()
  {
    cv::Mat frame;
    if (!cap_.read(frame)) {
      RCLCPP_ERROR(get_logger(), "Failed to capture frame from camera.");
      return;
    }

    auto msg =
      cv_bridge::CvImage(std_msgs::msg::Header(), "bgr8", frame).toImageMsg();
    msg->header.stamp = now();
    camera_image_pub_->publish(*msg);
  }

  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr camera_image_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
  cv::VideoCapture cap_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CameraNode>());
  rclcpp::shutdown();
  return 0;
}
