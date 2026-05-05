import rclpy #libraries for ROS2 in Python
from rclpy.node import Node 
from std_msgs.msg import String 

#creatting a node class that inherits from the Node in rclpy.node
class TestingNode(Node):
    def __init__(self):
        super().__init__('testing_node')
        self.subscriber = self.create_subscription(String, 'testing_topic', self.listener_callback, 10) 
        #node subscribing to the topic testing_topic with message type string, callback function will be called when data is received, and queu size of 10.

    def listener_callback(self, msg):
        self.get_logger().info(f'i heard: "{msg.data}"')
    
def main(args=None):
    rclpy.init(args=args)
    testing_node = TestingNode() #creating the node object
    try:
        rclpy.spin(testing_node) #execute the node and keep alive until shutdown
    except KeyboardInterrupt:
        pass
    finally:
        testing_node.destroy_node() #destroy the node when done
        rclpy.shutdown()
    
    
        