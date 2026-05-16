import rclpy
from pixhawk_packages.movement_node import MovementNode
import time
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy


class MotorTest(MovementNode):
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

        self.move(drive = 1600, duration = 5.0)

        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)




        self.get_logger().info("partially stopping NOW")

        self.move(duration = 5.0)

        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)



        self.get_logger().info("Test complete")



def main(args = None):
    rclpy.init(args=args)

    test = MotorTest()

    try: 
        test.run()
    except KeyboardInterrupt:
        pass
    finally:
        test.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

    


        


