from enum import Enum

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from testing_stuff.aligning_test import AligningTest
from testing_stuff.basic_test import BasicTest
from testing_stuff.depth_hold_test import DepthTest
from testing_stuff.semi_final import Semi
from testing_stuff.u_turn_test import UTurnTest


class State(Enum):
    SEMI = 1
    DEPTH_HOLD_TEST = 3
    ALIGNING_TEST = 4
    U_TURN_TEST = 5
    BASIC_TEST = 6


ACTIVE_MISSIONS = [State.SEMI]


class MissionNode(Node):
    def __init__(self):
        super().__init__("mission_node")



    def run(self):
        for state in ACTIVE_MISSIONS:
            if state == State.ALIGNING_TEST:
                AligningTest().run()
            elif state == State.DEPTH_HOLD_TEST:
                DepthTest().run()
            elif state == State.SEMI:
                Semi().run()
            elif state == State.U_TURN_TEST:
                UTurnTest().run()
            elif state == State.BASIC_TEST:
                BasicTest().run()


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


if __name__ == "__main__":
    main()
