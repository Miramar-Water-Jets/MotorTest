import math

import rclpy
from geometry_msgs.msg import (
    Quaternion,
    Vector3,  # for importing the vector3 message type to send imu data in euler degree
)
from mavros_msgs.msg import AttitudeTarget
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, Float64, UInt16MultiArray


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

        self.DIVE_SPEED = 1700
        self.current_depth = 0.0
        self.current_heading = 0.0
        self.heading_received = False
        self.current_status = False
        self.dive_timer = None

        self.motion_timer = None
        self.heading_timer = None
        self.heading_hold_timer = None

        self.end_time = None
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        qos_best_effort = QoSProfile(
            depth=10, reliability=ReliabilityPolicy.BEST_EFFORT
        )
        qos_latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.thruster_cmd_pub = self.create_publisher(
            UInt16MultiArray, "auv/thruster_cmd", qos
        )
        # In ALT_HOLD, ArduSub accepts an attitude target with thrust ignored.
        # This lets Pixhawk close the yaw loop while its depth controller remains active.
        self.attitude_target_pub = self.create_publisher(
            AttitudeTarget, "/mavros/setpoint_raw/attitude", qos
        )

        self.depth_sub = self.create_subscription(
            Float64, "/mavros/global_position/rel_alt", self.depth_cb, qos_best_effort
        )
        self.IMU_sub = self.create_subscription(
            Vector3, "/auv/imu", self.heading_cb, qos_best_effort
        )
        self.ready_sub = self.create_subscription(
            Bool, "/auv/ready", self.ready_cb, qos_latched
        )

    def depth_cb(self, msg):
        self.current_depth = abs(msg.data)

    def heading_cb(self, msg):
        self.current_heading = msg.z
        self.heading_received = True

    def ready_cb(self, msg):
        self.current_status = msg.data
        if not self.current_status:
            self.heading_received = False
            self.clear_heading_hold()

    def wait_until_ready(self):
        """Wait for armed ALT_HOLD and a fresh IMU heading."""
        while not (self.current_status and self.heading_received):
            rclpy.spin_once(self, timeout_sec=0.1)

    def countdown(self, seconds):
        """Run an operator countdown while processing readiness updates.

        Returns False if the vehicle becomes unready before the mission starts.
        """
        for remaining in range(seconds, 0, -1):
            if not self.current_status:
                self.get_logger().warn("AUV became unready; mission start cancelled")
                return False
            self.get_logger().info(f"Starting in {remaining}...")
            end_time = self.get_clock().now() + Duration(seconds=1.0)
            while self.get_clock().now() < end_time:
                rclpy.spin_once(self, timeout_sec=0.1)
                if not self.current_status:
                    self.get_logger().warn("AUV became unready; mission start cancelled")
                    return False
        self.get_logger().info("GO!")
        return True

    def send(self, drive=1500, strafe=1500, dive=1500, heading=1500):
        msg = UInt16MultiArray()

        msg.data = [65535] * 18
        msg.data[2] = dive
        msg.data[3] = heading
        msg.data[4] = drive
        msg.data[5] = strafe

        self.thruster_cmd_pub.publish(msg)

    def move(self, drive=1500, strafe=1500, dive=1500, heading=1500, duration=1.0):
        if self.motion_timer:
            self.motion_timer.cancel()
            self.motion_timer = None

        self._drive = drive
        self._strafe = strafe
        self._dive = dive
        self._heading = heading

        self.send(
            drive=self._drive,
            strafe=self._strafe,
            dive=self._dive,
            heading=self._heading,
        )

        self.end_time = self.get_clock().now() + Duration(seconds=duration)
        self.motion_timer = self.create_timer(0.05, self.motion_timer_callback)

    def dive_to_depth(self, target_depth, tolerance=0.1):
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
            dive_cmd = (
                self.DIVE_SPEED if depth_error < 0 else 1500 - (self.DIVE_SPEED - 1500)
            )
            self.send(dive=dive_cmd)

    def change_heading(self, target_heading, tolerance=5):
        """Ask ArduSub's attitude controller to turn to an absolute yaw target.

        This must be used in ALT_HOLD. The target ignores thrust, so ALT_HOLD
        retains depth control and RC forward/strafe inputs remain available.
        """
        self.target_heading = target_heading % 360.0
        self.tolerance = tolerance

        if self.motion_timer:
            self.destroy_timer(self.motion_timer)
            self.motion_timer = None

        if self.heading_timer:
            self.destroy_timer(self.heading_timer)
        if self.heading_hold_timer:
            self.destroy_timer(self.heading_hold_timer)
            self.heading_hold_timer = None

        self.heading_timer = self.create_timer(0.05, self.heading_timer_cb)

    def clear_heading_hold(self):
        """Stop publishing the native yaw target before taking manual yaw control."""
        if self.heading_timer:
            self.destroy_timer(self.heading_timer)
            self.heading_timer = None
        if self.heading_hold_timer:
            self.destroy_timer(self.heading_hold_timer)
            self.heading_hold_timer = None

    def publish_heading_target(self):
        half_yaw = math.radians(self.target_heading) / 2.0

        msg = AttitudeTarget()
        # Ignore body rates and thrust; provide an absolute orientation target.
        # ArduSub keeps the existing ALT_HOLD depth target when thrust is ignored.
        msg.type_mask = (
            AttitudeTarget.IGNORE_ROLL_RATE
            | AttitudeTarget.IGNORE_PITCH_RATE
            | AttitudeTarget.IGNORE_YAW_RATE
            | AttitudeTarget.IGNORE_THRUST
        )
        msg.orientation = Quaternion(
            x=0.0,
            y=0.0,
            z=math.sin(half_yaw),
            w=math.cos(half_yaw),
        )
        self.attitude_target_pub.publish(msg)

    def heading_timer_cb(self):
        heading_error = (self.target_heading - self.current_heading + 180) % 360 - 180

        if abs(heading_error) <= self.tolerance:
            self.destroy_timer(self.heading_timer)
            self.heading_timer = None
            # ArduSub discards attitude targets after a timeout. Keep the target
            # alive so it holds this heading while the mission resumes movement.
            self.heading_hold_timer = self.create_timer(0.2, self.publish_heading_target)
            return

        self.publish_heading_target()

    def motion_timer_callback(self):
        if self.get_clock().now() >= self.end_time:
            # RC override commands persist in ArduSub, so explicitly return all
            # axes to neutral before removing the timer.
            self.send()
            self.destroy_timer(self.motion_timer)
            self.motion_timer = None
        else:
            self.send(
                drive=self._drive,
                strafe=self._strafe,
                dive=self._dive,
                heading=self._heading,
            )


def main(args=None):
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


if __name__ == "__main__":
    main()
