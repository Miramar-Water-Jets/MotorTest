from testing_stuff.aligning_test import AligningTest
from testing_stuff.basic_test import BasicTest
from testing_stuff.depth_hold_test import DepthTest
from testing_stuff.square_pattern_test import SquarePatternTest

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from enum import Enum
import time

class State(Enum):
    SQUARE_TEST = 1
    BASIC_TEST = 2
    DEPTH_HOLD_TEST = 3
    ALIGNING_TEST = 4

ACTIVE_MISSIONS = [State.ALIGNING_TEST]

class MissionNode(Node):
    def __init__(self):
        super().__init__('mission_node')


    def countdown(self, seconds):
        for i in range(seconds, 0, -1):
            self.get_logger().info(f"Starting in {i}...")
            time.sleep(1)
        self.get_logger().info("GO!")


    def run(self):
        for state in ACTIVE_MISSIONS:
            if state == State.ALIGNING_TEST:
                self.countdown(5)
                AligningTest().run()
            elif state == State.DEPTH_HOLD_TEST:
                self.countdown(5)
                DepthTest().run()
            elif state == State.BASIC_TEST:
                self.countdown(5)
                BasicTest().run()
            elif state == State.SQUARE_TEST:
                self.countdown(5)
                SquarePatternTest().run()


def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()

