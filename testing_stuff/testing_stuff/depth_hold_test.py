# this is the testing for holding depth 
# command the AUV to dive down to depth of 1 meter and hold it for 15 sec
# commadn the AUV to move forward at that depth for 5 sec

import rclpy
from pixhawk_packages.movement_node import MovementNode
import time
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy

class DepthTest(MovementNode):
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


        # dive to depth 1 meter with the hardcoded speed of 1550, tolerance is + - 0.1 meter
        self.get_logger().info("Diving to depth now")
        self.dive_to_depth(target_depth=1.0, tolerance=0.1)
        while self.dive_timer is not None: # VERY IMPORTANT: use the dive_timer not motion_timer for this 
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done wdiving to depth")        


        # waiting for 15 seconds to check whether hold depth actually works
        self.get_logger().info("waiting for 15 sec now")
        self.move(duration = 15.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec = 0.05)
        self.get_logger().info("done waiting 15 sec")        

        # driving forward for 5 sec after holding depth
        self.get_logger().info(" moving forward at depth 1 meter underwater")
        self.move(drive = 1550, duration = 5.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec = 0.05)
        self.get_logger().info("done moving underwater")

        # waiting for one sec after moving forward at depth 1m
        self.get_logger().info("waiting for 1 sec now")
        self.move(duration = 1.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec = 0.05)
        self.get_logger().info("done waiting 1 sec")   

        # dive to depth 1 meter with the hardcoded speed of 1550, tolerance is + - 0.1 meter
        self.get_logger().info("turning to 90 degrees right now")
        self.change_heading(target_heading=90.0)
        while self.heading_timer is not None: # VERY IMPORTANT: use the heading_timer not motion_timer for this 
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done changing to heading 90 degrees to the right")        



        self.get_logger().info(" depth hold test complete")


def main(args = None):
    print("This function shouldn't be called")
    return

if __name__ == '__main__':
    main()

    