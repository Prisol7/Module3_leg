#!/usr/bin/env python3
"""
Thread-safe robot controller for Flask web application.
Extracted and adapted from Raspberry_Master_CLI.py
"""

import threading
import time

# Try to import smbus; if not available, run in "dry" mode
try:
    import smbus
except ImportError:
    smbus = None


class RobotPart:
    """Represents a single robot part (leg or joint)."""

    def __init__(self, label, angle=0.0, is_joint=False):
        self.label = label
        self.angle = float(angle)
        self.is_joint = is_joint
        self.relative_angle = 0.0 if is_joint else None
        self.initial_angle = float(angle)


class RobotController:
    """
    Thread-safe robot state and I2C communication manager.
    Controls 2 legs and 2 joints via I2C to Teensy.
    """

    def __init__(self, i2c_addr=0x08, bus_num=1):
        self.address = i2c_addr
        self.i2c_lock = threading.Lock()
        self.last_send_time = 0.0

        # Initial leg angle
        START_LEG_ANGLE = 45.0

        # Create parts: [left_leg, left_joint, right_leg, right_joint]
        self.parts = [
            RobotPart("Left Leg", angle=START_LEG_ANGLE),
            RobotPart("Left Joint", angle=START_LEG_ANGLE, is_joint=True),
            RobotPart("Right Leg", angle=START_LEG_ANGLE),
            RobotPart("Right Joint", angle=START_LEG_ANGLE, is_joint=True),
        ]

        # Align joints to legs (relative_angle = 0)
        for leg_idx in (0, 2):
            leg = self.parts[leg_idx]
            joint = self.parts[leg_idx + 1]
            joint.relative_angle = 0.0
            joint.angle = leg.angle + joint.relative_angle

        # Initialize I2C bus
        self.bus = None
        if smbus:
            try:
                self.bus = smbus.SMBus(bus_num)
                time.sleep(0.01)
            except Exception as e:
                print(f"Failed to initialize I2C bus: {e}")
                self.bus = None

    def set_leg(self, side, angle):
        """
        Set leg absolute angle within ±60° of initial (45°).
        Returns (success, message) tuple.
        """
        idx = 0 if side == "left" else 2
        leg = self.parts[idx]
        angle = float(angle)

        # Check if within allowed range
        angle_diff = ((angle - leg.initial_angle + 180) % 360) - 180
        if -60 <= angle_diff <= 60:
            leg.angle = angle
            # Update joint absolute angle
            joint = self.parts[idx + 1]
            joint.angle = leg.angle + joint.relative_angle
            return True, f"{leg.label} set to {leg.angle:.1f}"
        return False, "Angle out of allowed range (45 +/- 60)"

    def set_joint(self, side, rel_angle):
        """
        Set joint relative angle [0..60] degrees.
        Returns (success, message) tuple.
        """
        idx = 1 if side == "left" else 3
        joint = self.parts[idx]
        rel_angle = float(rel_angle)

        if 0.0 <= rel_angle <= 60.0:
            joint.relative_angle = rel_angle
            leg = self.parts[idx - 1]
            joint.angle = leg.angle + joint.relative_angle
            return True, f"{joint.label} relative angle set to {joint.relative_angle:.1f}"
        return False, "Relative angle must be between 0 and 60"

    def get_state_dict(self):
        """Return JSON-serializable state for all parts."""
        return {
            'left_leg': {
                'angle': self.parts[0].angle,
                'initial': self.parts[0].initial_angle
            },
            'left_joint': {
                'angle': self.parts[1].relative_angle
            },
            'right_leg': {
                'angle': self.parts[2].angle,
                'initial': self.parts[2].initial_angle
            },
            'right_joint': {
                'angle': self.parts[3].relative_angle
            }
        }

    def format_send_string(self):
        """
        Format data string for Teensy.
        Format: "left_joint/left_leg/right_joint/right_leg"
        Each value is 3-character padded integer.
        """
        left_joint = int(round(self.parts[1].relative_angle))
        left_leg = int(round(self.parts[0].angle))
        right_joint = int(round(self.parts[3].relative_angle))
        right_leg = int(round(self.parts[2].angle))
        return f"{left_joint:3}/{left_leg:3}/{right_joint:3}/{right_leg:3}"

    def send_data(self):
        """Send current state to Teensy via I2C (not thread-safe)."""
        send_str = self.format_send_string()
        print(f"SEND: {send_str}")

        if self.bus:
            try:
                data_bytes = send_str.encode("utf-8")
                self.bus.write_i2c_block_data(self.address, 0, list(data_bytes))
                self.last_send_time = time.time()
                return True
            except Exception as e:
                print(f"I2C write failed: {e}")
                return False
        else:
            print("(dry run, no I2C bus available)")
            self.last_send_time = time.time()
            return True

    def send_data_safe(self):
        """Thread-safe I2C send."""
        with self.i2c_lock:
            return self.send_data()


# For testing without Flask
if __name__ == "__main__":
    controller = RobotController()
    print("Initial state:", controller.get_state_dict())
    print("Send string:", controller.format_send_string())

    # Test setting leg
    success, msg = controller.set_leg("left", 60)
    print(f"Set left leg to 60: {msg}")
    print("State:", controller.get_state_dict())

    # Test setting joint
    success, msg = controller.set_joint("left", 30)
    print(f"Set left joint to 30: {msg}")
    print("State:", controller.get_state_dict())
    print("Send string:", controller.format_send_string())
