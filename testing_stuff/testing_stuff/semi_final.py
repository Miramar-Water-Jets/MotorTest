# main test to see if we can complete a square pattern for the competition
# the test goes as follow: 
# move the AUV to the right and pause
# move forward and pause
# move to the left and pause
# move backward and pause
# each movement and pausing is exactly 6 and 2 seconds apart

import rclpy
from pixhawk_packages.movement_node import MovementNode
import time
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy


class Semi(MovementNode):
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

        self.TARGET_DEPTH = 0.5

        # dive to depth 1 meter with the hardcoded speed of 1600, tolerance is + - 0.1 meter
        self.get_logger().info("Diving to depth now")
        self.dive_to_depth(target_depth=self.TARGET_DEPTH, tolerance=0.1)
        while (
            self.dive_timer is not None
        ):  # VERY IMPORTANT: use the dive_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done diving to depth")

        # moving forward for 3sec
        self.get_logger().info("moving forward for 5 sec")
        self.move(drive=1800, duration=3.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")

        #  turn 180 degrees to the right
        self.get_logger().info("turning to 180 degrees right now")
        target = (self.current_heading + 180) % 360
        self.change_heading(target_heading=target)
        while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done changing to heading 180 degrees to the right")
        self.get_logger().info(" depth hold test complete")

        #pause 2 sec
        self.get_logger().info("pausing for 2 sec")
        self.move(duration=2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing for 2 sec")

        #  turn 180 degrees to the right
        self.get_logger().info("turning to 180 degrees right now")
        target = (self.current_heading + 180) % 360
        self.change_heading(target_heading=target)
        while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done changing to heading 180 degrees to the right")
        self.get_logger().info(" depth hold test complete")

        # pause 2 sec
        self.get_logger().info("pausing for 2 sec")
        self.move(duration=2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing for 2 sec")

        # forward 10 sec
        self.get_logger().info("moving forward for 10 sec")
        self.move(drive=1800, duration=10.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")

        #  turn 180 degrees to the right
        self.get_logger().info("turning to 180 degrees right now")
        target = (self.current_heading + 180) % 360
        self.change_heading(target_heading=target)
        while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done changing to heading 180 degrees to the right")
        self.get_logger().info(" depth hold test complete")

        #pause 2 sec
        self.get_logger().info("pausing for 2 sec")
        self.move(duration=2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing for 2 sec")

        #  turn 180 degrees to the right
        self.get_logger().info("turning to 180 degrees right now")
        target = (self.current_heading + 180) % 360
        self.change_heading(target_heading=target)
        while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done changing to heading 180 degrees to the right")
        self.get_logger().info(" depth hold test complete")

        # pause 2 sec
        self.get_logger().info("pausing for 2 sec")
        self.move(duration=2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing for 2 sec")

        #  turn 180 degrees to the right
        self.get_logger().info("turning to 180 degrees right now")
        target = (self.current_heading + 180) % 360
        self.change_heading(target_heading=target)
        while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done changing to heading 180 degrees to the right")

        #forward 10 sec
        self.get_logger().info("moving forward for 10 sec")
        self.move(drive=1800, duration=10.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")

        self.get_logger().info("semi complete")
        
def main(args = None):
    print("This function shouldn't be called")
    return


if __name__ == '__main__':
    main()

    


        


