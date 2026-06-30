# test the basic fucntion of the motor and see if everyhting works as intended
# the test will first check the state and ensure connectivity, ALT_HOLD mode and arming
# move forward 2.5 sec, stop for 2 sec and *STRAFE AND DRIVE AT THE SAME TIME* for 2.5 sec

import rclpy
from pixhawk_packages.movement_node import MovementNode
import time
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy


class BasicTest(MovementNode):
    def __init__(self):
        super().__init__()
        self.current_status = False

        qos_latched = QoSProfile(depth = 1, reliability=ReliabilityPolicy.RELIABLE, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

        self.create_subscription(Bool, '/auv/ready', self.ready_cb,qos_latched)

    def ready_cb(self,msg):
        self.current_status = msg.data

    def run(self):
        while not self.current_status:
            rclpy.spin_once(self, timeout_sec = 0.1)
        self.get_logger().info("AUV is ready for testing")

        self.get_logger().info("going forward NOW")
        self.move(drive = 1550, duration = 2.5)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")


def main(args = None):
    print("This function shouldn't be called")
    return


if __name__ == '__main__':
    main()

    


       


