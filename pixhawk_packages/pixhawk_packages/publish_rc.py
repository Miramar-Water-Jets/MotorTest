import rclpy
from rclpy.time import Time
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy
from mavros_msgs.msg import OverrideRCIn
from std_msgs.msg import Bool, UInt16MultiArray
import time

class Publish_RC(Node):
    NEUTRAL_PWM = 1500
    CONTROL_CHANNELS = (2, 3, 4, 5)

    def __init__(self):

        super().__init__("publish_RC")

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        qos_latched = QoSProfile( depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

        self.channels = self.neutral_channels()
        self.current_status = False
        # Commands received before the current armed/ready cycle must never be
        # replayed as soon as the vehicle becomes armed.
        self.awaiting_fresh_command = True
        self.last_cmd_time = self.get_clock().now()

        self.RC_pub = self.create_publisher(OverrideRCIn, "/mavros/rc/override",qos)

        self.ready_sub = self.create_subscription(Bool, '/auv/ready', self.ready_cb, qos_latched)

        self.thurster_sub = self.create_subscription(UInt16MultiArray, '/auv/thruster_cmd', self.motor_cb, qos)

        self.publish_timer = self.create_timer(0.05, self.publish_override)

    @classmethod
    def neutral_channels(cls):
        channels = [65535] * 18
        for channel in cls.CONTROL_CHANNELS:
            channels[channel] = cls.NEUTRAL_PWM
        return channels

    def ready_cb(self, msg):
        was_ready = self.current_status
        self.current_status = msg.data

        if not self.current_status or not was_ready:
            self.channels = self.neutral_channels()
            self.awaiting_fresh_command = True
            self.last_cmd_time = self.get_clock().now()

    def motor_cb(self, msg):
        if len(msg.data) != 18:
            self.get_logger().warn("Ignoring malformed thruster command", throttle_duration_sec=1.0)
            return

        # Ignore pre-arm commands. The controller must explicitly send a new
        # command after readiness has been announced.
        if not self.current_status:
            return

        self.channels = list(msg.data)
        self.awaiting_fresh_command = False
        self.last_cmd_time = self.get_clock().now()

    def publish_override(self):
        msg = OverrideRCIn()

        now = self.get_clock().now()

        elapsed = (now - self.last_cmd_time).nanoseconds / 1e9

        if self.current_status == False:
            self.get_logger().warn("AUV is not ready, please do the startup sequence", throttle_duration_sec=1.0)

            msg.channels = self.neutral_channels()

            self.RC_pub.publish(msg)

            return
        
        if self.awaiting_fresh_command or elapsed > 0.5:
            self.get_logger().warn("have not received any movement for 0.5s, setting all to neutral ", throttle_duration_sec=1.0)

            msg.channels = self.neutral_channels()

            self.RC_pub.publish(msg)

            return
        
        else:
            msg.channels = self.channels

            self.RC_pub.publish(msg)

def main(args= None):
    rclpy.init(args=args)
    publish_RC = Publish_RC()

    import signal

    def send_neutral_burst(publish_RC_node):
        """Blast neutral RC override commands so the Pixhawk definitely gets one."""
        try:
            msg = OverrideRCIn()
            msg.channels = publish_RC_node.neutral_channels()
            # Send multiple times — the Pixhawk needs to actually receive one
            # before MAVROS dies from the same SIGINT
            for _ in range(10):
                publish_RC_node.RC_pub.publish(msg)
                time.sleep(0.05)
        except Exception:
            pass

    def sigint_handler(sig, frame):
        """Intercept SIGINT BEFORE rclpy tears down, stop motors first."""
        send_neutral_burst(publish_RC)
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        rclpy.spin(publish_RC)
    except KeyboardInterrupt:
        pass
    finally:
        # One more burst in case the signal handler didn't fully run
        send_neutral_burst(publish_RC)
        publish_RC.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()
