# main test to see if we can complete a square pattern for the competition
# the test goes as follow:
# move the AUV to the right and pause
# move forward and pause
# move to the left and pause
# move backward and pause
# each movement and pausing is exactly 6 and 2 seconds apart

import rclpy
from pixhawk_packages.movement_node import MovementNode


class Semi(MovementNode):
    def __init__(self):
        super().__init__()


    def run(self):
        self.wait_until_ready()
        self.get_logger().info("AUV is ready for testing")
        self.change_heading(self.current_heading)
        if not self.countdown(20):
            return

        self.TARGET_DEPTH = 1.0
        self.get_logger().info(f"Current heading: {self.current_heading}")

        # self.change_heading(target_heading=self.target_heading)

        # dive to depth 1 meter with the hardcoded speed of 1600, tolerance is + - 0.1 meter
        self.get_logger().info("Diving to depth now")
        self.dive_to_depth(target_depth=self.TARGET_DEPTH, tolerance=0.1)
        while (
            self.dive_timer is not None
        ):  # VERY IMPORTANT: use the dive_timer not motion_timer for this
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done diving to depth")

        self.target_heading = self.current_heading
        self.get_logger().info(f"Current heading: {self.current_heading}")

        # moving forward for 3sec
        self.get_logger().info("moving forward for 5 sec")
        self.move(drive=1800, duration=3.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")


        # pause 2 sec
        self.get_logger().info("pausing for 2 sec")
        self.move(duration=2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing for 2 sec")

        # forward 10 sec
        self.get_logger().info("moving forward for 10 sec")
        self.move(drive=1800, duration=18.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")


        for i in range(12):
            self.target_heading += 60
            self.target_heading %= 360

            self.get_logger().info(f"turning to {self.target_heading} ({i+1} of 6)")
            self.change_heading(target_heading=self.target_heading)
            while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
                rclpy.spin_once(self, timeout_sec=0.05)
            self.get_logger().info("Pausing for 0.2 sec")
            self.move(duration=0.2)
            while self.motion_timer is not None:
                rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done 360 degree turn")

        # pause 2 sec
        self.get_logger().info("pausing for 2 sec")
        self.move(duration=2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing for 2 sec")

        for i in range(3):
            self.target_heading += 60
            self.target_heading %= 360

            self.get_logger().info(f"turning to {self.target_heading} ({i+1} of 6)")
            self.change_heading(target_heading=self.target_heading)
            while (self.heading_timer is not None):  # VERY IMPORTANT: use the heading_timer not motion_timer for this
                rclpy.spin_once(self, timeout_sec=0.05)
            self.get_logger().info("Pausing for 0.2 sec")
            self.move(duration=0.2)
            while self.motion_timer is not None:
                rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done 180 degree turn")

        #forward 10 sec
        self.get_logger().info("moving forward for 10 sec")
        self.move(drive=1800, duration=18.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")



        self.get_logger().info("semi complete")

def main(args = None):
    print("This function shouldn't be called")
    return


if __name__ == '__main__':
    main()
