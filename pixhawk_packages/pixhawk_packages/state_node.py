#subscribing: mavros/state, mavros/battery
#publishing: None
# this node take data form stat eand battery topic, logg the infromation and print it out
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.node import Node
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool
from sensor_msgs.msg import BatteryState

class StateNode(Node):
    def __init__(self):
        super().__init__('state_node')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)  # define it first!
        self.state_subscriber = self.create_subscription(State, '/mavros/state', self.state_callback, qos)
        self.battery_subscriber = self.create_subscription(BatteryState, '/mavros/battery', self.battery_callback, qos)
        self.current_state = State()
        self.battery_status = BatteryState()

    def state_callback(self, msg):
        self.current_state = msg
        log_data = f"connection: {msg.connected}, arm: {msg.armed}, mode: {msg.mode}, system status: {msg.system_status}"
        self.get_logger().info(log_data, throttle_duration_sec=2.0)

    def battery_callback(self, msg):
        self.battery_status = msg
        # msg.percentage is 0.0 to 1.0, so multiply by 100 for readability
        log_data = f"battery percentage: {msg.percentage * 100:.1f}%"
        self.get_logger().info(log_data, throttle_duration_sec=2.0)

def main(args= None):
    rclpy.init(args=args)
    state_node = StateNode()
    try:
        rclpy.spin(state_node)
    except KeyboardInterrupt:
        pass
    finally:
        state_node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()




    
        

    
                
