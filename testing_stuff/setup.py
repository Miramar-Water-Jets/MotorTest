from setuptools import find_packages, setup

package_name = 'testing_stuff'

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
            'square_pattern_test = testing_stuff.square_pattern_test:main',
            'basic_test = testing_stuff.basic_test:main',
            'depth_hold_test = testing_stuff.depth_hold_test:main',
            'aligning_test = testing_stuff.aligning_test:main',
            'mission_node = testing_stuff.mission_node:main',
        ],
    },
)
