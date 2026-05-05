"""
this program uses Manual mode instead of guided 
I have the idea of using guided, but that fall short due to requirement of an external GPS
then i wrote the entire thing using ALT_HOLD mode
but that did ot workout either since I have move() function which can pass in dive param, but since ALT_HOLD does not allow change in the dive channel
I have no choice but to use manual
KEY DETAIL: manual requires the AUV to be boyantly neutral, or when someone can come up or create a PID control loop for this guy
-------------KEY FUNCTION--------------------
1) subcribing to mavros/state and auv/imu for startup sequence + getting orientation
2) pubishing data into RCOverride
3) have arming service + change mode service, each driving action has a timer or is timed based control
4) any function with cb is callback function, called imeadiatly after receiving data OR needing to check something
- startup_sequence(): check if pixhawk is connected, is in manual mode and if the it is amring, then armed or change mode, has 20 sec timer

- move(): consist of drive, sway, dive and turn motion, all time based (PWM and time)

- stop(): set all motors to neutral and all moving timer to None, essentially stopping the AUV movement

- turn(): change heading by taking data form IMU, user input degrees, PWM (HAVE TO BE ABOVE 1500!!) adn tolerance

- change_depth(): change depth by taking data from mavros rela_dept channel , user input negative depth, PWM (HAVE TO BE ABOVE 1500!!) and tolerance

- publish_override(): publishing every 0.05 sec to mavros/RC/override 
- arm(): amr/disarming (True = arm, False = disarm)
-set_mode(): changing mode 
"""


import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.duration import Duration
from mavros_msgs.msg import State, OverrideRCIn # to read the state before arming
from mavros_msgs.srv import CommandBool, SetMode #for amring and mode change services
from geometry_msgs.msg import Vector3                       #for importing the vector3 message type to send imu data in euler degree
from std_msgs.msg import Float64       # for depth topic - adjust if different msg type

class MotorNodeAltHold(Node):
    def __init__(self):
        super().__init__('motor_node')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)  

        #publishing to RC override, controlling the AUV
        self.motor_pub = self.create_publisher(OverrideRCIn,'/mavros/rc/override',qos)

        #subscribing to imu 
        self.imu_sub = self.create_subscription(Vector3,'/auv/imu',self.imu_cb, qos) 

        #subscribing to depth
        self.depth_sub = self.create_subscription(Float64,'/mavros/global_position/rel_alt', self.depth_cb,qos) 

        # subscribing to state
        self.state_sub = self.create_subscription(State,'/mavros/state',self.state_cb, qos) 

        self.current_state = State()
        self.current_yaw = 0.0
        self.current_depth = 0.0

        #safety start up timer for the AUV
        self.STARTUP_TIMEOUT = 20.0
        self.TURN_TIMEOUT  = 15.0
        self.DEPTH_TIMEOUT = 20.0
        self.startup_timeout_timer = self.create_timer(self.STARTUP_TIMEOUT, self.startup_timeout_cb)


        """status of indication that the AUV is curerntly in turning or changing depth"""
        self.turning = False
        self.changing_depth = False
        """initializing, no current target depth yet"""
        self.target_yaw = 0.0
        self.target_depth = 0.0
        """turn and depth timer no value yet, initialize"""
        self.turn_timer = None
        self.depth_timer = None
        """initialize turn and depth tolerance"""
        self.turn_tolerance = 3.0
        self.depth_tolerance = 0.1

        self.arm_client = self.create_client(CommandBool, '/mavros/cmd/arming') #creating an arming service
        self.mode_client = self.create_client(SetMode, '/mavros/set_mode') #creating a mode changing service

        self.channels = [0,0,1500,1500,1500,1500]

        self.timer = self.create_timer(0.05,self.publish_override)

        # getting the time limit for the starting sequence
        # it will go step by step checking the amrign status, if the sub is in ALT_HOLD mode and if the pixhawk is connected
        self.startup_timer = self.create_timer(1, self.startup_sequence) #calling the start up function each 1 sec
        self.ready_status = False #setting the arming status to false, will change once the startup sequence is complete

        self.motion_timer = None



    """callback functions to get the latest data from topic"""
    #call back function for state
    def state_cb(self, msg): 
        self.current_state = msg
    
    #call back function for yaw
    def imu_cb(self,msg):
        self.current_yaw = msg.z
    
    #call back function for depth
    def depth_cb(self,msg):
        self.current_depth = msg.data



    """
    - if the pixhawk is already good to go, meaning the ready status is all true after all conditions are met
    - the startup timer will be cancelled, no need to go through the arming sequence
    - ** ADDED ** 
    """
    def startup_sequence(self):
        #create a timer for start up, if past timer,abort and shutdown

        if self.ready_status == True:
            self.startup_timer.cancel()
            return
        #if Pixhawk is not connected to companion computer, a message will be printed until otherwise
        if not self.current_state.connected:
            self.get_logger().info("waiting for pixhawk comection")
            return
        #if the mode is not MANUAL, the it will change to the correct mode, which is MANUAL
        if self.current_state.mode != "MANUAL":
            self.get_logger().info("changing mode to MANUAL")
            self.set_mode("MANUAL")
            return
        # if the pixhawk is unarmed, the arming sequence will arm
        if self.current_state.armed == False:
            self.get_logger().info("arming the Pixhawk")
            self.arm(True)
            return
        #setting the condition to True once the pixhakw is connected, armned, and is in MANUAL mode
        self.ready_status = True

    """callback function that checks for the start up sequence, if ran out of time, shutdown"""
    def startup_timeout_cb(self):
        if self.ready_status:
            # started up fine, cancel the timeout
            self.startup_timeout_timer.cancel()
            self.startup_timeout_timer = None
            return
        
        # took too long, abort
        self.get_logger().error('Startup timed out, could not arm. Shutting down')
        self.startup_timeout_timer.cancel()
        self.startup_timer.cancel()
        rclpy.shutdown()
        



    """
    this is for the movement of the AUV, using PWM and time based 
    ---- neutral = 1500 -----

    drive = moving forward(>1500)/backward(<1500)
    sway = moving right(>1500)/left(<1500)
    dive = moving up(>1500)/down(<1500)
    heaidng = turning CW(>1500)/CCW(<1500)

    duration = thow long it is continuing that motion.
    """
    def move(self, drive = 1500, sway = 1500, dive = 1500, heading = 1500, duration = 1.0):
        if not self.ready_status:
            self.get_logger().warn('AUV not ready, startup incomplete')
            return
        if self.turning or self.changing_depth:
            self.get_logger().warn('Precision maneuver in progress, ignoring move()')
            return
        self.channels = [0,0,dive, heading, drive, sway] # setting the value input to PWM in the channel

        if self.motion_timer != None:
            self.motion_timer.cancel()

        self.end_time = self.get_clock().now() + Duration(seconds = duration)# get current time + how long turning
        self.motion_timer = self.create_timer(0.05, self._motion_timer_cb) #check of timer is reached

    """ check if timer is reached """
    def _motion_timer_cb(self):
        if self.get_clock().now() >= self.end_time:
            if not self.turning:
                self.channels[3] = 1500
            if not self.changing_depth:
                self.channels[2] = 1500
            self.channels[4] = 1500  # drive always reset
            self.channels[5] = 1500  # sway always reset
            self.motion_timer.cancel()
            self.motion_timer = None



    """
    ----function for turning the AUV to the specific headings----
    degrees = degrees it is turningEx: 90.0 = turn right, -90.0 = turn left from the dircetion it is facing)
    speed_PWM = the speed at which it is turning, 1600 is safe
    tolerance = uncertainty in exact degrees that is acceptable
    """
    def turn(self, degrees: float, speed_PWM = 1600, tolerance: float = 3.0):
        if not self.ready_status:
            self.get_logger().info("AUV not ready, please try again")
            return
        if self.turning:
            self.get_logger().info("AUV is turning now")
            return
        
        self.turn_end_time = self.get_clock().now() + Duration(seconds=self.TURN_TIMEOUT)  

        self.target_yaw = (self.current_yaw + degrees) % 360
        self.turn_tolerance = tolerance
        self.turning = True

        #check if speed is positive
        if degrees >= 0:
            heading_PWM = speed_PWM
        else:
            heading_PWM = 3000 - speed_PWM

        #publishing to RCoverride with the speed
        self.channels[3] = heading_PWM

        self.turn_timer = self.create_timer(0.05,self.turn_cb)

    """check and log the info to see if target yaw is reached"""
    def turn_cb(self):
        #compute difference in angle, too lazy to understand the math
        diff = (self.target_yaw - self.current_yaw + 180) % 360 - 180
        self.get_logger().info(f'yaw: {self.current_yaw:.1f} | target: {self.target_yaw:.1f} | diff: {diff:.1f}')

        if abs(diff) <= self.turn_tolerance:
            self.channels[3] = 1500      # stop turning
            self.turning = False
            self.turn_timer.cancel()
            self.turn_timer = None
            self.get_logger().info('Turn complete')

        elif self.get_clock().now() >= self.turn_end_time:
            self.channels[3] = 1500
            self.turning = False
            self.turn_timer.cancel()
            self.turn_timer = None
            self.get_logger().error('Turn timed out, aborting')



    """
    ----function for changing depth of the AUV to the specific depth----
    delta = depth it is changing Ex: 1 = go up, -1 = go down from current depth)
    speed_PWM = the speed at which it is changing, 1600 is safe
    tolerance = uncertainty in exact meters that is acceptable
    """
    def change_depth(self, delta: float, speed_PWM: int = 1600, tolerance: float = 0.1):
        # safety stuff
        if not self.ready_status:
            self.get_logger().info("AUV not ready, please try again")
            return
        if self.changing_depth:
            self.get_logger().info("AUV is already changing depth")
            return
        self.depth_end_time = self.get_clock().now() + Duration(seconds=self.DEPTH_TIMEOUT)  

        self.target_depth = self.current_depth + delta
        self.depth_tolerance = tolerance
        self.changing_depth = True

        # check if going deeper or shallower
        if delta > 0:
            dive_PWM = speed_PWM          # diving up
        else:
            dive_PWM = 3000 - speed_PWM   # going down

        # publishing to RCoverride with the speed
        self.channels[2] = dive_PWM
        self.depth_timer = self.create_timer(0.05, self.depth_cb_timer)

    """check and log the info to see if target depth is reached"""
    def depth_cb_timer(self):
        diff = self.target_depth - self.current_depth
        self.get_logger().info(f'depth: {self.current_depth:.2f}m | target: {self.target_depth:.2f}m | diff: {diff:.2f}m')

        if abs(diff) <= self.depth_tolerance:
            self.channels[2] = 1500       # stop diving
            self.changing_depth = False
            self.depth_timer.cancel()
            self.depth_timer = None
            self.get_logger().info('Depth change complete')

        elif self.get_clock().now() >= self.depth_end_time:
            self.channels[2] = 1500
            self.changing_depth = False
            self.depth_timer.cancel()
            self.depth_timer = None
            self.get_logger().error('Depth change timed out, aborting')



    """publishing the values in channels to the RC Override topic"""
    def publish_override(self):
        #checking the status and connectivity of the pixhawk, making sure everything is connected, or else will start the start up sequence
        if self.ready_status and not self.current_state.connected:
            self.get_logger().warn('Pixhawk disconnected, halting')
            self.ready_status = False
            self.stop()
            if self.startup_timer:
                self.startup_timer.cancel()
                self.startup_timer = None
            self.startup_timer = self.create_timer(1, self.startup_sequence)

        msg = OverrideRCIn()
        channels = self.channels
        if len(channels) < 18:
            channels.extend([0] * (18 - len(self.channels)))
        if len(channels) > 18:
            self.get_logger().warn("Somehow too many channels are present, aborting")
            return
        msg.channels = channels
        self.motor_pub.publish(msg)



    """
    using the pre existing mavros_msgs/CommandBool 
    service to return T/F commands to Mavlink to enabled autopilot
    """
    def arm(self, state:bool):
        req = CommandBool.Request() #define the type of request, which in this case is commandBool for autopilot enabling
        req.value = state # fills into the request, state is whatever we passed in for arm, true is armed, false is unarmed
        self.arm_client.call_async(req) #requesting the service

    """defining and calling the change mode service"""
    def set_mode(self, mode:str):
        req = SetMode.Request()
        req.custom_mode = mode
        self.mode_client.call_async(req)



    """
    stopping the all the movement, including turning, chanigng depth and everything. 
    setting all motors to neutral 1500, display a message
    """
    def stop(self):
        self.channels = [0,0,1500,1500,1500,1500] #setting all motors to neutral
        self.turning = False
        self.changing_depth = False
        if self.motion_timer:
            self.motion_timer.cancel()
            self.motion_timer = None
        if self.turn_timer:                 
            self.turn_timer.cancel()
            self.turn_timer = None
        if self.depth_timer:                
            self.depth_timer.cancel()
            self.depth_timer = None
        self.get_logger().info("stopping the motor, setting all motors to NEUTRAL")



"""main stuff"""
def main(args=None):
    rclpy.init(args=args)
    node = MotorNodeAltHold()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
