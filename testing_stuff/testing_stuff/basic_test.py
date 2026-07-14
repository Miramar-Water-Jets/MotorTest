# test the basic fucntion of the motor and see if everyhting works as intended
# the test will first check the state and ensure connectivity, ALT_HOLD mode and arming
# move forward 2.5 sec, stop for 2 sec and *STRAFE AND DRIVE AT THE SAME TIME* for 2.5 sec

import rclpy
from pixhawk_packages.movement_node import MovementNode


class BasicTest(MovementNode):
    def __init__(self):
        super().__init__()

    def run(self):
        self.wait_until_ready()
        self.get_logger().info("AUV is ready for testing")
        self.change_heading(self.current_heading)
        if not self.countdown(20):
            return

        #test forward movement
        self.get_logger().info("going forward NOW")
        self.move(drive = 1650, duration = 2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")

        #test pause
        self.get_logger().info("pausing for 2 sec")
        self.move(duration = 2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing")

if __name__ == '__main__':
    main()
