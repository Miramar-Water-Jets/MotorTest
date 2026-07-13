# this is the testing for holding depth
# command the AUV to dive down to depth of 1 meter and hold it for 15 sec
# commadn the AUV to move forward at that depth for 5 sec

import time

import rclpy
from pixhawk_packages.movement_node import MovementNode
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool


class DepthTest(MovementNode):
    def __init__(self):
        super().__init__()
        self.current_status = False

        qos_latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.create_subscription(Bool, "/auv/ready", self.ready_cb, qos_latched)

    def ready_cb(self, msg):
        self.current_status = msg.data

    def run(self):
        while not self.current_status:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info("AUV is ready for testing")

        self.TARGET_DEPTH = 0.5

        # dive to depth 1 meter with the hardcoded speed of 1600, tolerance is + - 0.1 meter
        self.get_logger().info("Diving to depth now")
        self.dive_to_depth(target_depth=self.TARGET_DEPTH, tolerance=0.1)
        while (
            self.dive_timer is not None
        ):  # VERY IMPORTANT: use the dive_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done diving to depth")

        # waiting for 10 seconds to check whether hold depth actually works
        self.get_logger().info("waiting for 1 sec now")
        self.move(duration=1.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done waiting 1 sec")

        # driving forward for 5 sec after holding depth
        self.get_logger().info(" moving forward at depth 1 meter underwater")
        self.move(drive=1800, duration=4.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving underwater")
        
        # waiting for one sec after moving forward at depth 1m
        self.get_logger().info("waiting for 1 sec now")
        self.move(duration=1.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done waiting 1 sec")

        # dive to depth 1 meter with the hardcoded speed of 1550, tolerance is + - 0.1 meter
        self.get_logger().info("turning to 90 degrees right now")
        target = (self.current_heading + 90) % 360
        self.change_heading(target_heading=target)
        while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done changing to heading 90 degrees to the right")
        self.get_logger().info(" depth hold test complete")

        # driving forward for 5 sec after holding depth
        self.get_logger().info(" moving forward at depth 1 meter underwater")
        self.move(drive=1800, duration=4.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving underwater")
        


def main(args=None):
    print("This function shouldn't be called")
    return


if __name__ == "__main__":
    main()
