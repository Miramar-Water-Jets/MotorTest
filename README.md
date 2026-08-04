# SleepyFishy 2.0

Platform for writing and documenting code for SleepyFishy 2.0, our AUV for RoboSub. 
This repo covers the PWM control stack, with logic separated by node.

## Pixhawk_packages

- **publish_rc.py** — the only node that talks to the motor via `/mavros/rc/override`. 
  Includes a 0.5s watchdog: if no PWM command is received in that window, it automatically 
  sends a neutral signal as a safety fallback.
- **movement.py** — standardizes movement across channels (x, y, z, r/heading). Includes 
  closed-loop control for exact depth holding and precise heading changes.
- **IMU_node.py** — reads orientation as a quaternion, converts yaw to Euler degrees using 
  `tf` transformations.
- **state_monitor.py** — checks connectivity and mode (ALT_HOLD), arms/disarms the Pixhawk.

## testing_stuff

- **basic_test** — spins motors for 2s at 1700µs PWM to verify correct direction and function.
- **depth_hold_test** — dives 1m and holds for 15s, then moves forward 1m and turns 90° right. 
  Validates closed-loop depth holding and heading control.
- **u_turn_test** — drives through the gate (qualification run logic).
- **aligning_test** — listens to `/bboxes_gate` to center on the gate and pass through, using 
  YOLO-based visual alignment instead of dead reckoning.
- **mission_node** — state machine that takes a mission input and runs it sequentially.
- **semi_final** — dive 1m, 360° turn in 60° increments, pass through gate, repeat turn, 
  return through gate (semifinal run logic).
