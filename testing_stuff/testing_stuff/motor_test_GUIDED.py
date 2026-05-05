"""
NOT YET USING

import rclpy
from motor_node import motor_Node

def main(args=None):
    rclpy.init(args=args)
    motor = motor_Node()

    # wait for arming and guided mode to complete
    while not motor.ready_status:
        rclpy.spin_once(motor)

    motor.move(drive=0.5, duration=3.0)     # drive forward for 3 seconds
    while motor.active:
        rclpy.spin_once(motor, timeout_sec=0.1)

    motor.move(side_move=0.5, duration=3.0)     # strafe right for 3 seconds
    while motor.active:
        rclpy.spin_once(motor, timeout_sec=0.1)

    motor.move(depth=-0.5, duration=3.0)     # dive down for 3 seconds
    while motor.active:
        rclpy.spin_once(motor, timeout_sec=0.1)

    motor.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
    
"""
