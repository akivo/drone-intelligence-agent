"""
Manual drone controller for AirSim.
Run this while Blocks.exe is open, then use keyboard to fly.

Controls:
  T       - Takeoff
  L       - Land
  W / S   - Fly forward / backward
  A / D   - Fly left / right
  Q / E   - Rotate (yaw) left / right
  R / F   - Fly up / down
  X       - Hover in place (stop all movement)
  H       - Print help
  ESC     - Land and exit
"""

import sys
import msvcrt  # Windows keyboard input (no install needed)
sys.path.insert(0, ".")

import airsim

SPEED     = 3    # m/s for all movement
STEP      = 3    # metres per keypress
ALT_STEP  = 2    # metres per up/down press
YAW_STEP  = 15   # degrees per rotate press


def print_help():
    print("""
  T       - Takeoff
  L       - Land
  W / S   - Forward / Backward
  A / D   - Left / Right
  R / F   - Up / Down
  Q / E   - Rotate left / right
  X       - Hover (stop)
  H       - Help
  ESC     - Land and quit
""")


def get_pos(c):
    state = c.getMultirotorState()
    p = state.kinematics_estimated.position
    return p.x_val, p.y_val, p.z_val


def main():
    print("Connecting to AirSim...")
    c = airsim.MultirotorClient()
    c.confirmConnection()
    c.enableApiControl(True)
    c.armDisarm(True)
    print("Connected. Press T to take off, H for help, ESC to quit.\n")

    flying = False

    while True:
        ch = msvcrt.getwch()

        key = ch.lower() if isinstance(ch, str) else ""

        # ESC key
        if ord(ch) == 27 if isinstance(ch, str) else ch == b'\x1b':
            print("ESC - Landing and exiting...")
            if flying:
                c.landAsync().join()
            c.armDisarm(False)
            break

        if key == "h":
            print_help()

        elif key == "t":
            if not flying:
                print("Taking off...")
                c.takeoffAsync().join()
                flying = True
                print("Airborne! Use W/A/S/D/R/F to fly.")
            else:
                print("Already flying.")

        elif key == "l":
            print("Landing...")
            c.landAsync().join()
            flying = False
            print("Landed.")

        elif key == "x":
            x, y, z = get_pos(c)
            c.moveToPositionAsync(x, y, z, velocity=1).join()
            print("Hovering.")

        elif flying:
            x, y, z = get_pos(c)

            if key == "w":
                print(f"Forward  -> x+{STEP}")
                c.moveToPositionAsync(x + STEP, y, z, velocity=SPEED).join()

            elif key == "s":
                print(f"Backward -> x-{STEP}")
                c.moveToPositionAsync(x - STEP, y, z, velocity=SPEED).join()

            elif key == "a":
                print(f"Left     -> y-{STEP}")
                c.moveToPositionAsync(x, y - STEP, z, velocity=SPEED).join()

            elif key == "d":
                print(f"Right    -> y+{STEP}")
                c.moveToPositionAsync(x, y + STEP, z, velocity=SPEED).join()

            elif key == "r":
                print(f"Up       -> z-{ALT_STEP}")
                c.moveToPositionAsync(x, y, z - ALT_STEP, velocity=SPEED).join()

            elif key == "f":
                print(f"Down     -> z+{ALT_STEP}")
                c.moveToPositionAsync(x, y, z + ALT_STEP, velocity=SPEED).join()

            elif key == "q":
                print(f"Rotate left  -{YAW_STEP} deg")
                c.rotateByYawRateAsync(-YAW_STEP, 1).join()

            elif key == "e":
                print(f"Rotate right +{YAW_STEP} deg")
                c.rotateByYawRateAsync(YAW_STEP, 1).join()

        else:
            if key in "wsadqref":
                print("Not flying yet - press T to take off first.")


if __name__ == "__main__":
    main()
