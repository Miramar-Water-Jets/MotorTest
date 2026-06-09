import rclpy
from rclpy.time import Time
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy
from mavros_msgs.msg import OverrideRCIn
from std_msgs.msg import Bool, UInt16MultiArray
import time

class Publish_RC(Node):
    def __init__(self):

        super().__init__("publish_RC")

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        qos_latched = QoSProfile( depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

        self.channels = [65535] * 18
        self.channels[2] = 1500
        self.channels[3] = 1500
        self.channels[4] = 1500
        self.channels[5] = 1500

        self.current_status = False

        self.last_cmd_time = self.get_clock().now()

        self.RC_pub = self.create_publisher(OverrideRCIn, "/mavros/rc/override",qos)

        self.ready_sub = self.create_subscription(Bool, '/auv/ready', self.ready_cb, qos_latched)

        self.thurster_sub = self.create_subscription(UInt16MultiArray, '/auv/thruster_cmd', self.motor_cb, qos)

        self.publish_timer = self.create_timer(0.05, self.publish_override)

    def ready_cb(self,msg):
        self.current_status = msg.data

    def motor_cb(self,msg):
        self.channels = list(msg.data)
        self.last_cmd_time = self.get_clock().now()

    def publish_override(self):
        msg = OverrideRCIn()

        now = self.get_clock().now()

        elapsed = (now - self.last_cmd_time).nanoseconds / 1e9

        if self.current_status == False:
            self.get_logger().warn("AUV is not ready, please do the startup sequence", throttle_duration_sec=1.0)

            msg.channels = [65535] * 18
            msg.channels[2] = 1500
            msg.channels[3] = 1500
            msg.channels[4] = 1500
            msg.channels[5] = 1500

            self.RC_pub.publish(msg)

            return
        
        if elapsed > 0.5:
            self.get_logger().warn("have not received any movement for 0.5s, setting all to neutral ", throttle_duration_sec=1.0)

            msg.channels = [65535] * 18
            msg.channels[2] = 1500
            msg.channels[3] = 1500
            msg.channels[4] = 1500
            msg.channels[5] = 1500

            self.RC_pub.publish(msg)

            return
        
        else:
            msg.channels = self.channels

            self.RC_pub.publish(msg)

def main(args= None):
    rclpy.init(args=args)
    publish_RC = Publish_RC()
    
    try:
        rclpy.spin(publish_RC)
    except KeyboardInterrupt:
        pass
    finally:
        msg = OverrideRCIn()
        msg.channels = [65535] * 18
        msg.channels[2] = 1500
        msg.channels[3] = 1500
        msg.channels[4] = 1500
        msg.channels[5] = 1500
        publish_RC.RC_pub.publish(msg)
        time.sleep(0.1)
        publish_RC.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()


