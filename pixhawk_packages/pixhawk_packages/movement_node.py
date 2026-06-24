import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from std_msgs.msg import UInt16MultiArray, Float64
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import Vector3                       #for importing the vector3 message type to send imu data in euler degree



class MovementNode(Node):
    """
    ---initialization that subscribe to depth topic and publish thruster command---
    """
    def __init__(self):
        super().__init__("movement_node")

        self._drive = 1500
        self._strafe = 1500
        self._dive = 65535
        self._heading = 1500

        self.DIVE_SPEED = 1550
        self.current_depth = 0.0
        self.current_heading = 0.0
        self.dive_timer = None

        self.motion_timer = None

        self.end_time = None 
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        qos_best_effort = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        self.thruster_cmd_pub = self.create_publisher(UInt16MultiArray,'auv/thruster_cmd',qos)

        self.depth_sub = self.create_subscription(Float64, '/mavros/global_position/rel_alt', self.depth_cb, qos_best_effort)
        self.IMU_sub = self.create_subscription(Vector3, '/auv/imu', self.heading_cb, qos_best_effort)





    def depth_cb(self,msg):
        self.current_depth = abs(msg.data)

    def heading_cb(self, msg):
        self.current_heading = msg.z




    def send(self, drive = 1500, strafe = 1500, dive = 1500, heading = 1500):
        msg = UInt16MultiArray()

        msg.data = [65535] * 18
        msg.data[2] = dive
        msg.data[3] = heading
        msg.data[4] = drive
        msg.data[5] = strafe

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





    def dive_to_depth(self, target_depth, tolerance = 0.1):
        self.target_depth = target_depth
        self.tolerance = tolerance
        if self.motion_timer:
            self.destroy_timer(self.motion_timer)
            self.motion_timer = None

        self.dive_timer = self.create_timer(0.05, self.dive_timer_cb)

    def dive_timer_cb(self):
        depth_error = self.target_depth - self.current_depth

        if abs(depth_error) <= self.tolerance:
            self.send(dive=1500)
            self.destroy_timer(self.dive_timer)
            self.dive_timer = None
        else:
            dive_cmd = self.DIVE_SPEED if depth_error < 0 else 1500 - (self.DIVE_SPEED - 1500)
            self.send(dive=dive_cmd)



    def change_heading(self, target_heading, tolerance = 5):
            self.target_heading = target_heading
            self.tolerance = tolerance
            if self.motion_timer:
                self.destroy_timer(self.motion_timer)
                self.motion_timer = None

            self.heading_timer = self.create_timer(0.05, self.heading_timer_cb)

    def heading_timer_cb(self):
        heading_error = self.target_heading - self.current_heading

        if abs(heading_error) <= self.tolerance:
            self.send(heading=1500)
            self.destroy_timer(self.heading_timer)
            self.heading_timer = None
        else:
            if heading_error > 0:
                heading_cmd = 1580
            else:
                heading_cmd = 1420

            self.send(heading=heading_cmd)


    def motion_timer_callback(self):
        if self.get_clock().now() >= self.end_time:
            self.destroy_timer(self.motion_timer) 
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
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()
        