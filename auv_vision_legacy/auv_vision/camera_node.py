import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import cv2


class CameraNode(Node):
    def __init__(self):
        super().__init__("CameraNode")
        self.get_logger().info("Camera node started!")
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)
        self.camera_image_pub = self.create_publisher(Image, "/auv/camera/image_raw", qos)
        self.bridge = CvBridge()


        self.cap = cv2.VideoCapture(0)  # Open the default camera (index 0)
        print(f"Camera opened: {self.cap.isOpened()}")

        if not self.cap.isOpened():
            self.get_logger().error("Could not open camera.")
            return

        self.create_timer(0.1, self.publish_frame)

    def publish_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().error("Failed to capture frame from camera.")
            return
        
        # Convert the OpenCV image (BGR) to ROS Image message
        ros_image = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        self.camera_image_pub.publish(ros_image)

def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()
    rclpy.spin(camera_node)
    camera_node.destroy_node()
    try:
        rclpy.shutdown()
    except Exception:
            pass
if __name__ == '__main__':
    main()
