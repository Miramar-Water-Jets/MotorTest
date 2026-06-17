from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    return LaunchDescription([

        Node(
            package='pixhawk_packages',
            executable='publish_rc',
            name='publish_rc',
            output='screen'
        ),

        Node(
            package='pixhawk_packages',
            executable='state_monitor',
            name='state_monitor',
            output='screen'
        ),

         Node(
            package='pixhawk_packages',
            executable='movement_node',
            name='movement_node',
            output='screen'
        ),

        Node(
            package='auv_vision',
            executable='camera_node',
            name='camera_node',
            output='screen'
        ),

        Node(
            package='auv_vision',
            executable='detection_node',
            name='detection_node',
            output='screen'
        ),
        
        Node(
            package='testing_stuff',
            executable='mission_node',
            name='mission_node',
            output='screen'
        )
    ])