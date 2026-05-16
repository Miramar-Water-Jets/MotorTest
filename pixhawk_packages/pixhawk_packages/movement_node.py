import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from std_msgs.msg import Bool, UInt16MultiArray
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy


class MovementNode(Node):

    def __init__(self):
        super().__init__("movement_node")

        self._drive = 1500
        self._strafe = 1500
        self._dive = 1500
        self._heading = 1500

        self.motion_timer = None   

        self.end_time = None 
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)

        self.thruster_cmd_pub = self.create_publisher(UInt16MultiArray,'auv/thruster_cmd',qos)

    def send(self, drive = 1500, strafe = 1500, dive = 1500, heading = 1500):
        msg = UInt16MultiArray()

        channels = [1500] * 18

        channels[2] = dive
        channels[3] = heading
        channels[4] = drive
        channels[5] = strafe

        msg.data = channels

        self.thruster_cmd_pub.publish(msg)

    def move(self,drive = 1500, strafe = 1500, dive = 1500, heading = 1500, duration = 1.0):
        if self.motion_timer:
            self.motion_timer.cancel()
            self.motion_timer = None

        self._drive = drive
        self._strafe = strafe
        self._dive = dive
        self._heading = heading

        self.send(drive=self._drive, strafe=self._strafe, dive=self._dive, heading=self._heading)

        self.end_time = self.get_clock().now() + Duration(seconds = duration)
        self.motion_timer = self.create_timer(0.05, self.motion_timer_callback)

    def motion_timer_callback(self):
        if self.get_clock().now() >= self.end_time:
            self.destroy_timer(self.motion_timer)  # use destroy_timer instead
            self.motion_timer = None
        else:
            self.send(drive=self._drive, strafe=self._strafe,
            dive=self._dive, heading=self._heading)


def main(args= None):
    rclpy.init(args=args)
    movement_node = MovementNode()
    try:
        rclpy.spin(movement_node)
    except KeyboardInterrupt:
        pass
    finally:
        movement_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
        

