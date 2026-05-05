from setuptools import find_packages, setup

package_name = 'pixhawk_packages'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='trancaominhtri',
    maintainer_email='trancaominhtri@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'IMU_node = pixhawk_packages.IMU_node:main',
            'state_node = pixhawk_packages.state_node:main',
            'motor_node_alt_hold = pixhawk_packages.motor_node_alt_hold:main',
        ],
    },
)
