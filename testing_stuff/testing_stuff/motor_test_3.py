#testing the motor node with abstraction layer
# remember the sequence of writing mission code:
# 1) create motor_node instance
# 2) create auv controller instance with motor node as argument
# 3) spin the motor node in a separate thread
# 4) auv.wait_ready() to start
# 5) auv is for movement and motor is for logging
# 6) always have safety measures.
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
        motor.get_logger().info("checking if motors are ready")
        auv.wait_ready()  # this must be here
        motor.get_logger().info("motors are ready")

        motor.get_logger().info("moving forward NOW")
        auv.forward(duration = 6.0)
        motor.get_logger().info("testing the stop function")
        auv.stop()
        time.sleep(1.0)
        motor.get_logger().info("testing complete")

        """
        motor.get_logger().info("moving right NOW")
        auv.strafe_right(duration=5.0)
        
        auv.forward(duration=3.0)
        motor.get_logger().info("moving forward")

        auv.strafe_left(duration=3.0)
        motor.get_logger().info("moving left")

        auv.backward(duration=3.0)
        motor.get_logger().info("moving backward")

        auv.strafe_right(duration=3.0)
        motor.get_logger().info("moving right")

        auv.stop()
        """

    except KeyboardInterrupt:
        motor.get_logger().info("program stopped. motors are set to neutral and disarm")
        time.sleep(0.5)  #give some time for auv to stop
        auv.stop()
        time.sleep(1.0)
        motor.arm(False)
        time.sleep(1.5)
    finally:
        motor.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()