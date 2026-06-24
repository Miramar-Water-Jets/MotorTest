# testing aligning node
#      

import rclpy
from rclpy.node import Node
import time
from std_msgs.msg import Bool, Float32MultiArray
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, QoSDurabilityPolicy
from pixhawk_packages.movement_node import MovementNode


class AligningTest(MovementNode):
    def __init__(self):
        
        super().__init__()

        self.frame_c_x = 320
        self.frame_c_y = 240

        self.SPEED_CONST_X = 0.1
        self.SPEED_CONST_Y = 0.1

        self.last_detection_time = None

        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)
        qos_latched = QoSProfile( depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

        self.detection_sub = self.create_subscription(Float32MultiArray,"/auv/camera/bboxes_gate",self.detection_cb, qos)
        self.ready_sub = self.create_subscription(Bool,'/auv/ready',self.ready_cb, qos_latched)

        self.current_status = False
        self.detection_data = None



    def ready_cb(self,msg):
        self.current_status = msg.data

    def detection_cb(self,msg):
        self.detection_data = msg.data
        self.last_detection_time = time.time()



    def run(self):
       
        while not self.current_status:
            rclpy.spin_once(self, timeout_sec = 0.1)
        self.get_logger().info("AUV is ready for testing")

        target_count = 0
        end_count = 0
        actually_seeing_gate = False
        
        # diving down 1 meter first to go thorugh the gate
        self.get_logger().info("Diving to depth now")
        self.dive_to_depth(target_depth=1.0, tolerance=0.1)
        while self.dive_timer is not None: # VERY IMPORTANT: use the dive_timer not motion_timer for this 
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done diving to depth")    

        self.get_logger().info("pausing for 2 sec")
        self.move(duration = 2.0)
        while self.motion_timer is not None:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.get_logger().info("done pausing")
        

        # THE ALIGNING PORTION OF THE CODE
        while True:
            rclpy.spin_once(self, timeout_sec=0.1)

            detected = (self.last_detection_time is not None and time.time() - self.last_detection_time < 0.5)

            if detected:

                self.get_logger().info(f"Received detection data")
                
                x1, y1, x2, y2, conf = self.detection_data

                end_count = 0

                if conf > 0.5:
                    target_count += 1
                else: 
                    target_count = 0

                self.get_logger().info(f"target count: {target_count}, end count: {end_count}")


                center_gate_x = (x1 + x2)/2
                center_gate_y = (y1 + y2)/2

                pwm_x = 1500 + (center_gate_x - self.frame_c_x) * 0.1
                pwm_x = int(max(1300, min(1700, pwm_x)))

                pwm_y = 1500 + (center_gate_y - self.frame_c_y) * 0.1
                pwm_y = int(max(1300, min(1700, pwm_y)))

                self.move(drive = 1550, strafe = pwm_x, dive = pwm_y, duration = 0.1)
                while self.motion_timer is not None:
                    rclpy.spin_once(self, timeout_sec=0.05)

                if target_count > 15:
                    actually_seeing_gate = True


            else:

                self.detection_data = None

                self.get_logger().warn("No detection data received, cannot align to gate.")
                self.get_logger().info(f"target count: {target_count}, end count: {end_count}")

                target_count = 0
                end_count += 1

                self.move(drive = 1550, duration = 0.1)
                while self.motion_timer is not None:
                    rclpy.spin_once(self, timeout_sec=0.05)

                if actually_seeing_gate == True and end_count >= 5:
                    self.get_logger().info("the auv has passed through the gate")
                    self.move(duration = 2.0)
                    while self.motion_timer is not None:
                        rclpy.spin_once(self, timeout_sec=0.05)
                    actually_seeing_gate = False
                    break


        self.get_logger().info("Aligning task complete.")



def main(args=None):
    print("This function shouldn't be called")
    return

if __name__ == "__main__":
    main()

        
