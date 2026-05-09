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
        auv.get_logger().info("waiting for motors to be ready")
        auv.wait_ready()  # this must be here
        auv.get_logger().info("motors are ready")

        auv.forward(duration = 6.0)
        auv.get_logger().info("moving forward")

        """auv.strafe_right(duration=3.0)
        auv.get_logger().info("moving right")

        auv.forward(duration=3.0)
        auv.get_logger().info("moving forward")

        auv.strafe_left(duration=3.0)
        auv.get_logger().info("moving left")

        auv.backward(duration=3.0)
        auv.get_logger().info("moving backward")

        auv.strafe_right(duration=3.0)
        auv.get_logger().info("moving right")

        auv.stop()"""

    except KeyboardInterrupt:
        auv.get_logger().info("program stopped. motors are set to neutral and disarm")
    finally:
        auv.stop()
        time.sleep(1.0)
        motor.arm(False)
        time.sleep(1.5)
        motor.destroy_node()
        rclpy.shutdown()