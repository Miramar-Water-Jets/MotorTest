import rclpy
from rclpy.node import Node
from mavros_msgs.srv import CommandBool, SetMode 
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy
from mavros_msgs.msg import State
from std_msgs.msg import Bool


class StateMonitor(Node):
    def __init__(self):
        super().__init__("State_Monitor_node")

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        sub_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)


        self.state_sub = self.create_subscription(State,'/mavros/state',self.state_cb, sub_qos) 

        self.current_state = State()

        self.ready_pub = self.create_publisher(Bool, '/auv/ready', qos)

        self.arm_client = self.create_client(CommandBool, '/mavros/cmd/arming') #creating an arming service
        self.mode_client = self.create_client(SetMode, '/mavros/set_mode') #creating a mode changing service

        self.ready_status = False

        self.startup_timer = self.create_timer(1.0, self.start_up_sequence)

    def state_cb(self, msg):
        self.current_state = msg


    def start_up_sequence(self):

        if not self.current_state.connected:
            self.get_logger().info("pixhawk is not connected. Please try again")
            return
        elif self.current_state.mode != "MANUAL":
            self.get_logger().info("pixhawk is not in MANUAL mode, chaning mode NOW")
            self.change_mode("MANUAL")
            return
        elif self.current_state.armed is not True:
            self.get_logger().info("amring the pixhawk NOW")
            self.arm(True)
            return
        
        self.set_ready(True)
        self.startup_timer.cancel()


    def set_ready(self, status: Bool):
        if self.ready_status != status:
            self.ready_status = status
            msg = Bool()
            msg.data = status
            self.ready_pub.publish(msg)

    def arm(self, state:Bool):
        req = CommandBool.Request()
        req.value = state
        self.arm_client.call_async(req)
        return True
    
    def change_mode(self, mode: str):
        req = SetMode.Request()
        req.custom_mode = mode
        self.mode_client.call_async(req)
        return True
    
def main(args= None):
    rclpy.init(args=args)
    state_monitor = StateMonitor()
    try:
        rclpy.spin(state_monitor)
    except KeyboardInterrupt:
        pass
    finally:
        state_monitor.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()
    