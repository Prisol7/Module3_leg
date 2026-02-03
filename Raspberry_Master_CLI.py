#!/usr/bin/env python3
# CLI replacement for the original Tkinter robot dog controller.
# Minimal memory usage: no GUI, simple interactive command loop.

import math
import time
import sys

# Try to import smbus; if not available, run in "dry" mode (prints instead of sending).
try:
    import smbus
except Exception:
    smbus = None

class RobotDogPart:
    def __init__(self, label, length=0, angle=0.0, is_wheel=False, is_joint=False):
        self.label = label
        self.length = length
        self.angle = float(angle)          # absolute angle for legs; for joints we keep relative separately
        self.is_wheel = is_wheel
        self.is_joint = is_joint
        self.speed = 0 if is_wheel else None
        self.relative_angle = 0.0 if is_joint else None
        self.initial_angle = float(angle)

class RobotDogCLI:
    def __init__(self, i2c_addr=0x08, bus_num=1, autosend=False, send_interval=0.1):
        # Create minimal parts list (no graphics)
        START_LEG_ANGLE = 45.0
        self.parts = [
            RobotDogPart("Left Leg", length=120, angle=START_LEG_ANGLE),
            RobotDogPart("Left Joint", length=100, angle=START_LEG_ANGLE, is_joint=True),
            RobotDogPart("Right Leg", length=120, angle=START_LEG_ANGLE),
            RobotDogPart("Right Joint", length=100, angle=START_LEG_ANGLE, is_joint=True),
            RobotDogPart("Left Wheel", length=50, is_wheel=True),
            RobotDogPart("Right Wheel", length=50, is_wheel=True),
        ]

        # Align joints to legs: relative_angle = 0
        for leg_idx in (0, 2):
            leg = self.parts[leg_idx]
            joint = self.parts[leg_idx + 1]
            joint.relative_angle = 0.0
            joint.angle = leg.angle + joint.relative_angle
            leg.initial_angle = leg.angle
            joint.initial_angle = joint.angle

        self.address = i2c_addr
        self.send_interval = send_interval
        self.last_send_time = 0.0
        self.autosend = autosend

        if smbus:
            try:
                self.bus = smbus.SMBus(bus_num)
                time.sleep(0.01)
            except Exception:
                self.bus = None
        else:
            self.bus = None

    def set_leg(self, side, angle):
        """Set leg absolute angle within +/-60 degrees of initial."""
        idx = 0 if side == "left" else 2
        leg = self.parts[idx]
        angle = float(angle)
        angle_diff = ((angle - leg.initial_angle + 180) % 360) - 180
        if -60 <= angle_diff <= 60:
            leg.angle = angle
            # update joint absolute angle
            joint = self.parts[idx + 1]
            joint.angle = leg.angle + joint.relative_angle
            self._autosend_maybe()
            return True, f"{leg.label} set to {leg.angle:.1f}°"
        return False, "angle out of allowed range (initial ±60°)"

    def set_joint(self, side, rel_angle):
        """Set joint relative angle [0..60] degrees."""
        idx = 1 if side == "left" else 3
        joint = self.parts[idx]
        rel_angle = float(rel_angle)
        if 0.0 <= rel_angle <= 60.0:
            joint.relative_angle = rel_angle
            leg = self.parts[idx - 1]
            joint.angle = leg.angle + joint.relative_angle
            self._autosend_maybe()
            return True, f"{joint.label} relative angle set to {joint.relative_angle:.1f}°"
        return False, "relative angle must be between 0 and 60°"

    def set_wheel(self, side, speed):
        """Set wheel speed (int). Typically -1, 0, 1 in original logic."""
        idx = 4 if side == "left" else 5
        wheel = self.parts[idx]
        wheel.speed = int(speed)
        self._autosend_maybe()
        return True, f"{wheel.label} speed set to {wheel.speed}"

    def status(self):
        lines = []
        for p in self.parts:
            if p.is_wheel:
                lines.append(f"{p.label}: speed={p.speed}")
            elif p.is_joint:
                lines.append(f"{p.label}: rel={p.relative_angle:.1f}°, abs={p.angle:.1f}°")
            else:
                lines.append(f"{p.label}: angle={p.angle:.1f}°")
        return "\n".join(lines)

    def format_send_string(self):
        # Format expected by Teensy Slave: left_joint/left_leg/right_joint/right_leg
        # Teensy reads tokens into angle_0..angle_3 and maps them to servos:
        # servo_0 = left joint, servo_1 = left leg, servo_2 = right joint, servo_3 = right leg
        left_joint = int(round(self.parts[1].relative_angle))
        left_leg = int(round(self.parts[0].angle))
        right_joint = int(round(self.parts[3].relative_angle))
        right_leg = int(round(self.parts[2].angle))
        send_value = f"{left_joint:3}/{left_leg:3}/{right_joint:3}/{right_leg:3}"
        return send_value

    def send_data(self):
        s = self.format_send_string()
        print("SEND:", s)
        b = s.encode("utf-8")
        if self.bus:
            try:
                # write block (register 0) like original
                self.bus.write_i2c_block_data(self.address, 0, list(b))
            except Exception as e:
                print("I2C write failed:", e)
        else:
            print("(dry run, no I2C bus available)")
        self.last_send_time = time.time()

    def _autosend_maybe(self):
        if self.autosend and (time.time() - self.last_send_time) >= self.send_interval:
            self.send_data()

def print_help():
    print("""
Commands:
  help                       Show this help.
  status                     Show current parts status.
  set leg left|right <deg>   Set left/right leg absolute angle (limited to initial±60°).
  set joint left|right <deg> Set left/right joint relative angle (0..60°).
  set wheel left|right <s>   Set wheel speed (integer, e.g. -1/0/1).
  send                       Send current leg/joint data over I2C.
  autosend on|off            Toggle automatic send on changes.
  exit | quit                Exit program.
""".strip())

def repl(cli):
    print("Robot Dog CLI. Type 'help' for commands.")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        if cmd in ("exit", "quit"):
            break
        if cmd == "help":
            print_help()
            continue
        if cmd == "status":
            print(cli.status())
            continue
        if cmd == "send":
            cli.send_data()
            continue
        if cmd == "autosend":
            if len(parts) >= 2:
                val = parts[1].lower()
                cli.autosend = (val == "on")
                print("autosend", "on" if cli.autosend else "off")
            else:
                print("usage: autosend on|off")
            continue
        if cmd == "set" and len(parts) >= 4:
            what = parts[1].lower()
            side = parts[2].lower()
            val = parts[3]
            if what == "leg" and side in ("left", "right"):
                ok, msg = cli.set_leg(side, val)
                print(msg)
                continue
            if what == "joint" and side in ("left", "right"):
                ok, msg = cli.set_joint(side, val)
                print(msg)
                continue
            if what == "wheel" and side in ("left", "right"):
                ok, msg = cli.set_wheel(side, val)
                print(msg)
                continue
        print("Unknown command. Type 'help'.")

def main():
    # Minimal argument handling: allow --dry to avoid I2C attempts, --autosend to enable autosend.
    autosend = False
    busnum = 1
    addr = 0x08
    args = sys.argv[1:]
    if "--autosend" in args:
        autosend = True
    if "--addr" in args:
        try:
            idx = args.index("--addr")
            addr = int(args[idx + 1], 0)
        except Exception:
            pass
    if "--bus" in args:
        try:
            idx = args.index("--bus")
            busnum = int(args[idx + 1])
        except Exception:
            pass

    cli = RobotDogCLI(i2c_addr=addr, bus_num=busnum, autosend=autosend)
    repl(cli)
    print("Exiting.")

if __name__ == "__main__":
    main()
