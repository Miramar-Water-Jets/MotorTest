# this code is the motor node for the AUV
# we are going to use GUIDED mode instead of MANUAL mode to help with PID control
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import TwistStamped #for velocity setpoint messages
from mavros_msgs.msg import State # to read the state before arming
from mavros_msgs.srv import CommandBool, SetMode #for amring and mode change services
import time

class Motor_Node(Node):
    def __init__(self):
        super().__init__('motor_node')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)  
        self.motor_pub = self.create_publisher(TwistStamped,'/mavros/setpoint_velocity/cmd_vel', 10) #publishing the motor setpoint to this mavros topic
        self.state_sub = self.create_subscription(State,'/mavros/state',self.state_cb, qos) # subscribing to sttae to get AUV state info for sequence start up 
        self.current_state = State()

        self.arm_client = self.create_client(CommandBool, '/mavros/cmd/arming') #creating an arming service
        self.mode_client = self.create_client(SetMode, '/mavros/set_mode') #creating a mode changing service

        #very important, publishing the setpoint intot the MAVROS topic at a 20Hz rate
        self.target = TwistStamped() #define target as the type of coordinate to be publshed
        self.timer = self.create_timer(0.05, self.publish_setpoint) #established a timer that every 0.05s will call publish setpoint

        #get the service for amring and change mode ready
        self.get_logger().info("getting the service for amring and change mode ready")
        self.arm_client.wait_for_service() #sgetting the arming client to ready to receive service request
        self.mode_client.wait_for_service()# getting the mode changing service to get ready for service request

        # getting the time limit for the starting sequence
        # it will go step by step checking the amrign status, if the sub is in guided mode and if the pixhawk is connected
        self.startup_timer = self.create_timer(1, self.startup_sequence) #calling the start up function each 1 sec
        self.ready_status = False #setting the arming status to false, will change once the startup sequence is complete

        self.active = False
        self.end_time = 0.0

    def state_cb(self, msg): #call back function for state to get the latest data
        self.current_state = msg

    def publish_setpoint(self):
        now = self.get_clock().now().nanoseconds / 1e9
        if self.active and now > self.end_time:
            self.stop()
            self.active = False
        self.target.header.stamp = self.get_clock().now().to_msg() #This line timestamps the message before publishing it.
        self.motor_pub.publish(self.target) #publishing target into the /mavros/setpoint_velocity/cmd_vel topic

    def startup_sequence(self):
        # if the pixhawk is already good to go, meaning the ready status is all true after all conditions are met
        # the startup timer will be cancelled, no need to go through the arming sequence
        if self.ready_status == True:
            self.startup_timer.cancel()
            return
        #if Pixhawk is not connected to companion computer, a message will be printed until otherwise
        if not self.current_state.connected:
            self.get_logger().info("waiting for pixhawk comection")
            return
        #if the mode is not GUIDED, the it will change to the correct mode, which is GUIDED
        if self.current_state.mode != "GUIDED":
            self.get_logger().info("changing mode to GUIDED")
            self.set_mode("GUIDED")
            return
        # if the pixhawk is unarmed, the arming sequence will arm
        if self.current_state.armed == False:
            self.get_logger().info("arming the Pixhawk")
            self.arm(True)
            return
        #setting the condition to True once the pixhakw is connected, armned, and is in GUIDED mode
        self.ready_status = True

    #using the preexisting mavros_msgs/CommandBool service to return T/F commands to Mavlink to enabled autopilot
    def arm(self, state:bool):
        req = CommandBool.Request() #define the type of request, which in this case is commandBool for autopilot enabling
        req.value = state # fills into the request, state is whatever we passed in for arm, true is armed, false is unarmed
        self.arm_client.call_async(req) #requesting the service

    #defining and calling the change mode service
    def set_mode(self, mode:str):
        req = SetMode.Request()
        req.custom_mode = mode
        self.mode_client.call_async(req)

    #defining movement. at its neutral state, everything is set to 0. once there are input from the /mavros/setpoint_velocity/cmd_vel topic, the 
    def move(self, drive = 0.0, side_move = 0.0, depth = 0.0, heading = 0.0, duration = None):
        self.target.twist.linear.x = drive #twist is for controlling the velocity, linear is moving parrallel to the axis, in this case is x axis
        self.target.twist.linear.y = side_move # moving parallel to the y axis
        self.target.twist.linear.z = depth # moving parallel to the z axis
        self.target.twist.angular.z = heading # angular is mving around the axis, VERY IMPORTANT, this is an rad/sec
        if duration is not None:  
            self.active = True
            self.end_time = self.get_clock().now().nanoseconds / 1e9 + duration
    #defining the stop function for the AUV
    def stop(self):
        self.target.twist.linear.x = 0.0
        self.target.twist.linear.y = 0.0
        self.target.twist.linear.z = 0.0
        self.target.twist.angular.z = 0.0 

    #ending the movement sequence
    def destroy_node(self):
        self.stop()
        end_time = time.time() + 0.5
        while time.time() < end_time:
            self.publish_setpoint()
            time.sleep(0.05)
        self.arm(False)
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    motor_node = motor_Node()

    try: 
        rclpy.spin(motor_node)
    except KeyboardInterrupt:
        pass
    finally:
        motor_node.destroy_node()
        rclpy.shutdown()
    
if __name__ == '__main__':
    main()
    """