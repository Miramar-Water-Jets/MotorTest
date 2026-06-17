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


class SquarePatternTest(MovementNode):
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

        # going to the right speed 1550 for 6s 
        self.get_logger().info("going to the right now")
        self.move(strafe = 1550, duration = 6.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done going to the right")

        # pausing 2s
        self.get_logger().info("pausing for 2 sec")
        self.move(duration = 2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing")

        # moving forward speed 1550 for 6 sec
        self.get_logger().info("going forward now")
        self.move(drive = 1550, duration = 6.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done moving forward")

        # pausing 2s
        self.get_logger().info("pausing for 2 sec")
        self.move(duration = 2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing")

        # going ot the left PWM 1450 for 6s
        self.get_logger().info("going to the left now")
        self.move(strafe = 1450, duration = 6.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done going to the left")

        # pausing 2s
        self.get_logger().info("pausing for 2 sec")
        self.move(duration = 2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing")

        # going backward PWM 1450
        self.get_logger().info("going backward now")
        self.move(drive = 1450, duration = 6.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done going backward")

        self.get_logger().info("square pattern complete")
        
def main(args = None):
    rclpy.init(args=args)

    test = SquarePatternTest()

    try: 
        test.run()
    except KeyboardInterrupt:
        pass
    finally:
        test.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()

    


        


