import rclpy                                                #libraries for ROS2 in Python
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.node import Node                                 #for importing the Node clas to create a node
from sensor_msgs.msg import Imu                             #for importing the imu message type
import transforms3d.euler as euler                           #for cvonverting quternion to euler degree for easier use in auv
from geometry_msgs.msg import Vector3                       #for importing the vector3 message type to send imu data in euler degree

# not yet setup.py , colcon build or source, remember to do these later
# this node serves as a subscriber to mavros/imu/data topic, which then publishes to the auv/imu topic 
# the node convert the quternion from the pixhawk to euler degree for easier use

class IMUNode(Node):
    def __init__(self):
        super().__init__('imu_node') #creating a node with the name imu_node
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.subscriber = self.create_subscription(Imu, 'mavros/imu/data', self.imu_callback, qos) 
        #creating  a subscriber and listen to imu data from mavros/imu/data topic, when data is received will call imu_callback function, queue size is 10

        self.publisher = self.create_publisher(Vector3, 'auv/imu', qos)
        #creating a publisher to publish imu data in euler degree to auv/imu topic, message type is vector3, queue size is 10
    def imu_callback(self,msg):
        orientation_q = msg.orientation
        orientation  = [orientation_q.w, orientation_q.x, orientation_q.y, orientation_q.z] #extracting the imu data in quaternion form into a list
        roll, pitch, yaw = euler.quat2euler(orientation) #converting the quaternion into euler radian
        imu_msg = Vector3() #creating vector3 message type 
        imu_msg.x = roll * 180.0 / 3.14159    #converting the roll from radian to degree
        imu_msg.y = pitch  * 180.0 / 3.14159  #converting the pitch from radian to degree
        imu_msg.z = yaw  * 180.0 / 3.14159    #converting the yaw from radian to degree
        self.publisher.publish(imu_msg) #publishing the vector3 message type into the auv/imu topic

def main(args= None):
    rclpy.init(args=args)
    imu_node = IMUNode() #creating the node object
    try:
        rclpy.spin(imu_node) #execute the node and keep aloive until shutdown
    except KeyboardInterrupt:
        pass
    finally:
        imu_node.destroy_node() #destroy and shutdown when done
        rclpy.shutdown()

if __name__ == '__main__': #execute the main function when this file is run directly
    main()

