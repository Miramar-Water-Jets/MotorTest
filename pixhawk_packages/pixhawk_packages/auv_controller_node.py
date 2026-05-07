"""
abstraction layer for controlling the AUV, eliminating the need to have while motion timer
"""
import time
from pixhawk_packages.motor_node_manual import Motor_Node

class AUVControllerNode:
    def __init__(self, motor: Motor_Node):
        self._m = motor

    def wait_ready(self, timeout=30.0):
        start = time.time()
        while not self._m.ready_status:
            if time.time() - start > timeout:
                raise TimeoutError("AUV never became ready")
            time.sleep(0.1)
        time.sleep(1.0)

    def forward(self, duration=1.0, speed=1600):
        self._m.move(drive=speed, duration=duration)
        self._wait_motion()

    def backward(self, duration=1.0, speed=1400):
        self._m.move(drive=speed, duration=duration)
        self._wait_motion()

    def strafe_right(self, duration=1.0, speed=1600):
        self._m.move(sway=speed, duration=duration)
        self._wait_motion()

    def strafe_left(self, duration=1.0, speed=1400):
        self._m.move(sway=speed, duration=duration)
        self._wait_motion()

    def turn_right(self, degrees=90, speed=1600):
        self._m.turn(degrees=abs(degrees), speed_PWM=speed)
        self._wait_turn()

    def turn_left(self, degrees=90, speed=1600):
        self._m.turn(degrees=-abs(degrees), speed_PWM=speed)
        self._wait_turn()

    def dive(self, delta, speed=1600):
        self._m.change_depth(delta=delta, speed_PWM=speed)
        self._wait_depth()

    def stop(self):
        self._m.stop()

    def _wait_motion(self, poll=0.05):
        while self._m.motion_timer is not None:
            time.sleep(poll)

    def _wait_turn(self, poll=0.05):
        while self._m.turning:
            time.sleep(poll)

    def _wait_depth(self, poll=0.05):
        while self._m.changing_depth:
            time.sleep(poll)