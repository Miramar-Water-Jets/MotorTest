import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import UInt16MultiArray
import sys, tty, termios, select

# Key bindings:
# w/s -> drive forward/backward
# a/d -> strafe left/right
# q/e -> turn left/right
# j/k -> dive down/up
# any other key / no key -> all neutral

NEUTRAL = 1500
SPEED = 1550   # forward/positive direction
SPEED_REV = 1450  # backward/negative direction

KEY_BINDINGS = {
    'w': ('drive', SPEED),
    's': ('drive', SPEED_REV),
    'a': ('strafe', SPEED_REV),
    'd': ('strafe', SPEED),
    'q': ('heading', SPEED_REV),
    'e': ('heading', SPEED),
    'j': ('dive', SPEED),
    'k': ('dive', SPEED_REV),
}


class TeleopNode(Node):
    def __init__(self):
        super().__init__("teleop_node")
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.thruster_cmd_pub = self.create_publisher(UInt16MultiArray, '/auv/thruster_cmd', qos)

        self.settings = termios.tcgetattr(sys.stdin)
        self.get_logger().info(
            "Teleop started. WS=drive, AD=strafe, QE=turn, JK=dive. CTRL+C to quit."
        )

        self.timer = self.create_timer(0.05, self.loop)

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
        key = sys.stdin.read(1) if rlist else ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def loop(self):
        key = self.get_key()

        drive = NEUTRAL
        strafe = NEUTRAL
        heading = NEUTRAL
        dive = NEUTRAL

        if key in KEY_BINDINGS:
            channel, value = KEY_BINDINGS[key]
            if channel == 'drive':
                drive = value
            elif channel == 'strafe':
                strafe = value
            elif channel == 'heading':
                heading = value
            elif channel == 'dive':
                dive = value
        elif key == '\x03':  # CTRL+C
            self.send_neutral()
            raise KeyboardInterrupt

        self.send(drive=drive, strafe=strafe, dive=dive, heading=heading)

    def send(self, drive=NEUTRAL, strafe=NEUTRAL, dive=NEUTRAL, heading=NEUTRAL):
        msg = UInt16MultiArray()
        msg.data = [65535] * 18
        msg.data[2] = dive
        msg.data[3] = heading
        msg.data[4] = drive
        msg.data[5] = strafe
        self.thruster_cmd_pub.publish(msg)

    def send_neutral(self):
        self.send()


def main(args=None):
    rclpy.init(args=args)
    teleop_node = TeleopNode()
    try:
        rclpy.spin(teleop_node)
    except KeyboardInterrupt:
        pass
    finally:
        teleop_node.send_neutral()
        teleop_node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()