import rclpy
from rclpy.node import Node 
from std_msgs.msg import Float32MultiArray
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import cv2
from ultralytics import YOLO

class DetectionNode(Node):
    def __init__(self):
        super().__init__("DetectionNode")

        self.get_logger().info("Detection node started!")
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)

        #path_to_YOLO = '/Users/trancaominhtri/robostack/auv_vision/auv_vision/best.pt'
        #path_YOLO_hand = '/Users/trancaominhtri/Downloads/best_hand.pt' #use this for testing purposes
        path_YOLO_hand = '/home/nvidia/robostack/best_hand.pt'

        self.bridge = CvBridge()

        self.model = YOLO(path_YOLO_hand)

        self.image_sub = self.create_subscription(Image, "/auv/camera/image_raw", self.image_cb, qos)

        self.detection_pub = self.create_publisher(Image, "/auv/camera/image_detected", qos)

        self.gate_pub= self.create_publisher(Float32MultiArray,'/auv/camera/bboxes_gate',qos)



    def image_cb(self, msg):
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        results = self.model(cv_image, verbose=False)

        """     used only for visualization purposes
        annotated_frame = results[0].plot()
        annotated_frame = cv2.resize(annotated_frame, (640, 360))
        cv2.imshow("detection", annotated_frame)
        cv2.waitKey(10)
        """

        boxes = results[0].boxes
        if len(boxes) == 0:
            return

        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            print(f"cls: {cls}, conf: {conf}")  #####
            bbox_msg = Float32MultiArray()
            bbox_msg.data = [x1, y1, x2, y2, conf]

            if cls == 0:
                self.gate_pub.publish(bbox_msg)
        """if more classes are added, add new bounding box publisher for that class and use elif to publish to the correct topic """


def main(args=None):
    rclpy.init(args=args)
    detection_node = DetectionNode()
    rclpy.spin(detection_node)
    detection_node.destroy_node()
    try:
        rclpy.shutdown()
    except Exception:
        pass
if __name__ == "__main__":  
    main()
