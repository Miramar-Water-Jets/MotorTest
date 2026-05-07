#testing the motor node with abstraction layer
import rclpy
from pixhawk_packages.auv_controller_node import AUVControllerNode
from pixhawk_packages.motor_node_manual import Motor_Node
import time
import threading

def main():
    rclpy.init()
    motor = Motor_Node()
    auv = AUVControllerNode(motor)

    spin_thread = threading.Thread(target=rclpy.spin, args=(motor,), daemon=True)
    spin_thread.start()

    try:
        auv.wait_ready()  # this must be here
        auv.forward(duration = 3.0)
        auv.strafe_right(duration=3.0)
        auv.forward(duration=3.0)
        auv.strafe_left(duration=3.0)
        auv.backward(duration=3.0)
        auv.strafe_right(duration=3.0)
        auv.stop()
    except KeyboardInterrupt:
        auv.get_logger().into("program stopped. motors are set to neutral and disarm")
    finally:
        auv.stop()
        time.sleep(1.0)
        motor.arm(False)
        time.sleep(1.5)
        motor.destroy_node()
        rclpy.shutdown()