# this is the testing for diving down, driving forward, turning around 180
# degrees, and driving back before rising to the surface
# dive to depth of 1 meter, drive forward at 1800 for 10 sec, turn around
# exactly 180 degrees, drive forward at 1800 for 10 sec, then rise back up

import time

import rclpy
from pixhawk_packages.movement_node import MovementNode
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool


class UTurnTest(MovementNode):
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

        # dive down to 1 meter, tolerance is +- 0.1 meter
        self.get_logger().info("Diving to depth now")
        self.dive_to_depth(target_depth=self.TARGET_DEPTH, tolerance=0.2)
        while (
            self.dive_timer is not None
        ):  # VERY IMPORTANT: use the dive_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done diving to depth")

        # waiting for 1 sec after diving to depth
        self.get_logger().info("waiting for 1 sec now")
        self.move(duration=2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done waiting 1 sec")

        # driving forward for 10 sec at depth
        self.get_logger().info("moving forward at depth 1 meter underwater")
        self.move(drive=1800, duration=20.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward underwater")

        # waiting for 1 sec after moving forward
        self.get_logger().info("waiting for 1 sec now")
        self.move(duration=1.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done waiting 1 sec")


def main(args=None):
    print("This function shouldn't be called")
    return


if __name__ == "__main__":
    main()
