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
from mavros_msgs.srv import CommandBool, SetMode #for arming and mode change services
from geometry_msgs.msg import Vector3                       #for importing the vector3 message type to send imu data in euler degree
from std_msgs.msg import Float64       # for depth topic - adjust if different msg type
import threading

class Motor_Node(Node):
    def __init__(self):
        super().__init__('motor_node')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        best_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        #publishing to RC override, controlling the AUV
        self.motor_pub = self.create_publisher(OverrideRCIn,'/mavros/rc/override',qos)

        #subscribing to imu 
        self.imu_sub = self.create_subscription(Vector3,'/auv/imu',self.imu_cb, best_qos) 

        #subscribing to depth
        self.depth_sub = self.create_subscription(Float64,'/mavros/global_position/rel_alt', self.depth_cb,best_qos) 

        # subscribing to state
        self.state_sub = self.create_subscription(State,'/mavros/state',self.state_cb, best_qos) 

        self.current_state = State()
        self.current_yaw = 0.0
        self.current_depth = 0.0

        #safety start up timer for the AUV
        self.STARTUP_TIMEOUT = 20.0
        self.TURN_TIMEOUT  = 15.0
        self.DEPTH_TIMEOUT = 20.0

        # set a single startup deadline and a single periodic startup checker
        self.start_time = self.get_clock().now()
        self.startup_deadline = self.start_time + Duration(seconds=self.STARTUP_TIMEOUT)
        self.startup_timer = self.create_timer(1.0, self.startup_sequence)

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

        # thread-safety lock for shared state (channels, timers, flags)
        self.lock = threading.Lock()

        # define PWM safety bounds
        self.MIN_PWM = 1100
        self.MAX_PWM = 1900

        # normalize channels to 18 elements (safe default), first 6 meaningful, rest zeros
        self.channels = [0,0,1500,1500,1500,1500] + [0]*12

        self.timer = self.create_timer(0.05,self.publish_override)

        # getting the time limit for the starting sequence
        # it will go step by step checking the arming status, if the sub is in ALT_HOLD mode and if the pixhawk is connected
        # (startup_timer already created above)
        self.ready_status = False #setting the arming status to false, will change once the startup sequence is complete

        self.motion_timer = None
        self.shutdown_requested = False



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


    def startup_sequence(self):
        # Single periodic startup check that also enforces deadline
        if self.ready_status:
            if self.startup_timer:
                self.startup_timer.cancel()
                self.startup_timer = None
            return

        now = self.get_clock().now()
        if now >= self.startup_deadline:
            self.get_logger().error('Startup timed out, attempting safe disarm and requesting shutdown')
            # attempt to disarm; arm() is non-blocking (call_async) and will try service with short timeout
            try:
                self.arm(False)
            except Exception:
                self.get_logger().error('Failed to request disarm')
            # ensure timers are cleaned up
            if self.startup_timer:
                self.startup_timer.cancel()
                self.startup_timer = None
            # request main to exit cleanly; avoid calling rclpy.shutdown() inside callback
            self.shutdown_requested = True
            return

        #if Pixhawk is not connected to companion computer, a message will be printed until otherwise
        if not self.current_state.connected:
            self.get_logger().info("waiting for pixhawk connection")
            return
        #if the mode is not MANUAL, then change to MANUAL with safer service handling
        if self.current_state.mode != "MANUAL":
            self.get_logger().info("changing mode to MANUAL")
            ok = self.set_mode("MANUAL")
            if not ok:
                self.get_logger().warn("set_mode service unavailable; retrying")
            return
        # if the pixhawk is unarmed, the arming sequence will arm (safe service handling)
        if self.current_state.armed == False:
            self.get_logger().info("arming the Pixhawk")
            ok = self.arm(True)
            if not ok:
                self.get_logger().warn("arming service unavailable; retrying")
            return
        #setting the condition to True once the pixhawk is connected, armed, and is in MANUAL mode
        self.ready_status = True


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

        # warn if requested PWMs out of allowed range
        for name, val in (("drive", drive), ("sway", sway), ("dive", dive), ("heading", heading)):
            if val < self.MIN_PWM or val > self.MAX_PWM:
                self.get_logger().warn(f'{name} PWM {val} outside safe range [{self.MIN_PWM},{self.MAX_PWM}]')

        # only update first six channels, keep the rest intact (protected by lock)
        with self.lock:
            self.channels[:6] = [0,0,dive, heading, drive, sway]

            if self.motion_timer != None:
                try:
                    self.motion_timer.cancel()
                except Exception:
                    pass

            self.end_time = self.get_clock().now() + Duration(seconds = duration)# get current time + how long turning
            self.motion_timer = self.create_timer(0.05, self._motion_timer_cb) #check of timer is reached

    """ check if timer is reached """
    def _motion_timer_cb(self):
        if self.get_clock().now() >= self.end_time:
            with self.lock:
                if not self.turning:
                    self.channels[3] = 1500
                if not self.changing_depth:
                    self.channels[2] = 1500
                self.channels[4] = 1500  # drive always reset
                self.channels[5] = 1500  # sway always reset
                if self.motion_timer:
                    try:
                        self.motion_timer.cancel()
                    except Exception:
                        pass
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

        if heading_PWM < self.MIN_PWM or heading_PWM > self.MAX_PWM:
            self.get_logger().warn(f'heading PWM {heading_PWM} outside safe range [{self.MIN_PWM},{self.MAX_PWM}]')

        # publishing to RCoverride with the speed (protected by lock)
        with self.lock:
            self.channels[3] = heading_PWM

            if self.turn_timer:
                try:
                    self.turn_timer.cancel()
                except Exception:
                    pass
            self.turn_timer = self.create_timer(0.05,self.turn_cb)

    """check and log the info to see if target yaw is reached"""
    def turn_cb(self):
        #compute difference in angle
        diff = (self.target_yaw - self.current_yaw + 180) % 360 - 180
        self.get_logger().info(f'yaw: {self.current_yaw:.1f} | target: {self.target_yaw:.1f} | diff: {diff:.1f}')

        if abs(diff) <= self.turn_tolerance:
            with self.lock:
                self.channels[3] = 1500      # stop turning
                self.turning = False
                if self.turn_timer:
                    try:
                        self.turn_timer.cancel()
                    except Exception:
                        pass
                    self.turn_timer = None
            self.get_logger().info('Turn complete')

        elif self.get_clock().now() >= self.turn_end_time:
            with self.lock:
                self.channels[3] = 1500
                self.turning = False
                if self.turn_timer:
                    try:
                        self.turn_timer.cancel()
                    except Exception:
                        pass
                    self.turn_timer = None
            self.get_logger().error('Turn timed out, aborting')


    """
    ----function for changing depth of the AUV to the specific depth----
    delta = depth it is changing Ex: 1 = go up, -1 = go down from current depth)
    speed_PWM = the speed at which it is changing, 1600 is safe
    tolerance = uncertainty in exact meters that is acceptable
    """
    def change_depth(self, delta: float, speed_PWM: int = 1600, tolerance: float = 0.1):
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

        if delta > 0:
            dive_PWM = speed_PWM          # diving up
        else:
            dive_PWM = 3000 - speed_PWM   # going down

        if dive_PWM < self.MIN_PWM or dive_PWM > self.MAX_PWM:
            self.get_logger().warn(f'dive PWM {dive_PWM} outside safe range [{self.MIN_PWM},{self.MAX_PWM}]')

        with self.lock:
            self.channels[2] = dive_PWM
            if self.depth_timer:
                try:
                    self.depth_timer.cancel()
                except Exception:
                    pass
            self.depth_timer = self.create_timer(0.05, self.depth_cb_timer)

    """check and log the info to see if target depth is reached"""
    def depth_cb_timer(self):
        diff = self.target_depth - self.current_depth
        self.get_logger().info(f'depth: {self.current_depth:.2f}m | target: {self.target_depth:.2f}m | diff: {diff:.2f}m')

        if abs(diff) <= self.depth_tolerance:
            with self.lock:
                self.channels[2] = 1500       # stop diving
                self.changing_depth = False
                if self.depth_timer:
                    try:
                        self.depth_timer.cancel()
                    except Exception:
                        pass
                    self.depth_timer = None
            self.get_logger().info('Depth change complete')

        elif self.get_clock().now() >= self.depth_end_time:
            with self.lock:
                self.channels[2] = 1500
                self.changing_depth = False
                if self.depth_timer:
                    try:
                        self.depth_timer.cancel()
                    except Exception:
                        pass
                    self.depth_timer = None
            self.get_logger().error('Depth change timed out, aborting')


    def _clamp_pwm(self, val:int):
        # clamp to tightened PWM values to avoid extremes (use 1100-1900 per request)
        return int(min(max(val, self.MIN_PWM), self.MAX_PWM))

    """publishing the values in channels to the RC Override topic"""
    def publish_override(self):
        # checking the status and connectivity of the pixhawk, making sure everything is connected, or else will start the start up sequence
        if self.ready_status and not self.current_state.connected:
            self.get_logger().warn('Pixhawk disconnected, halting')
            self.ready_status = False
            self.stop()
            # safely reset startup timer and deadline
            if self.startup_timer:
                try:
                    self.startup_timer.cancel()
                except Exception:
                    pass
                self.startup_timer = None
            self.start_time = self.get_clock().now()
            self.startup_deadline = self.start_time + Duration(seconds=self.STARTUP_TIMEOUT)
            self.startup_timer = self.create_timer(1.0, self.startup_sequence)

        # prepare a safe trimmed/padded list of 18 channels
        # copy under lock to avoid concurrent modification
        with self.lock:
            channels = list(self.channels[:18])  # trim if longer
        if len(channels) < 18:
            channels.extend([0] * (18 - len(channels)))  # pad if shorter

        # clamp commonly used PWM channels (indices 2-5)
        for i in (2,3,4,5):
            channels[i] = self._clamp_pwm(channels[i])

        msg = OverrideRCIn()
        msg.channels = channels
        self.motor_pub.publish(msg)


    """
    using the pre existing mavros_msgs/CommandBool 
    service to return T/F commands to Mavlink to enabled autopilot
    """
    def arm(self, state:bool):
        # wait a short while for the service to be available, avoid blocking the fast publish loop
        try:
            available = self.arm_client.wait_for_service(timeout_sec=0.5)
        except Exception:
            available = False
        if not available:
            self.get_logger().error('Arming service not available')
            return False
        req = CommandBool.Request()
        req.value = state
        self.arm_client.call_async(req)
        return True

    """defining and calling the change mode service"""
    def set_mode(self, mode:str):
        try:
            available = self.mode_client.wait_for_service(timeout_sec=0.5)
        except Exception:
            available = False
        if not available:
            self.get_logger().error('SetMode service not available')
            return False
        req = SetMode.Request()
        req.custom_mode = mode
        self.mode_client.call_async(req)
        return True


    """
    stopping the all the movement, including turning, chanigng depth and everything. 
    setting all motors to neutral 1500, display a message
    """
    def stop(self):
        # set first six back to neutral while preserving rest
        with self.lock:
            self.channels[:6] = [0,0,1500,1500,1500,1500]
            self.turning = False
            self.changing_depth = False
            if self.motion_timer:
                try:
                    self.motion_timer.cancel()
                except Exception:
                    pass
                self.motion_timer = None
            if self.turn_timer:                 
                try:
                    self.turn_timer.cancel()
                except Exception:
                    pass
                self.turn_timer = None
            if self.depth_timer:                
                try:
                    self.depth_timer.cancel()
                except Exception:
                    pass
                self.depth_timer = None
        self.get_logger().info("stopping the motor, setting all motors to NEUTRAL")



"""main stuff"""
def main(args=None):
    rclpy.init(args=args)
    node = Motor_Node()
    try:
        # spin in a loop and check for shutdown requests from callbacks
        while rclpy.ok() and not getattr(node, 'shutdown_requested', False):
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        rclpy.shutdown()

if __name__ == '__main__':
    main()
