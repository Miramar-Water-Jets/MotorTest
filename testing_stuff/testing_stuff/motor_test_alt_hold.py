"""
motor testing code, eliminate all the unecessary sway/ eevyrhting for now and focus mainly on drive with veyr much safety
one of the problem of interest is with the rclpy.spin() havign to handle both the motion timer call and the rclpy.spin_once
"""
import rclpy
from pixhawk_packages.motor_node_alt_hold import MotorNodeAltHold
import threading
import time

def main(args=None):
    MOTOR_READY_STATUS = 1.0
    CHECKING_MOTION_TIMER_TIME = 0.05
    rclpy.init(args=args)
    motor = MotorNodeAltHold()

    #thread that runs simultaneous ly to handle 
    spin_thread =  threading.Thread(target=rclpy.spin, args=(motor,), daemon=True)
    spin_thread.start()

    try: 
        #checking the status of the motor and set to arm, ALT_HOLD and check connectivity
        while not motor.ready_status:
            time.sleep(MOTOR_READY_STATUS)  
        motor.get_logger().info("AUV is ready, Preparing for motor test")

        motor.move(drive=1600, duration=3.0)     # drive forward for 3 seconds
        ######### time.sleep(0.1)
        while motor.motion_timer is not None:
            time.sleep(CHECKING_MOTION_TIMER_TIME)

        motor.move(sway=1400, duration=3.0)     # strafe right for 3 seconds
        time.sleep(0.1)
        while motor.motion_timer is not None:
            time.sleep(CHECKING_MOTION_TIMER_TIME)


        motor.get_logger().info('Drive test complete')


    except KeyboardInterrupt:
        motor.get_logger().info("program stopped. motors are set to neutral and disarm") 
        

    finally: 
        #set the motor to neutral
        motor.stop()
        #allows a one second time sleep
        time.sleep(1.0)
        #settign arm mode to false
        motor.arm(False)
        #destroy and shutdown
        time.sleep(1.5)  # give it time to actually send
        motor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()




