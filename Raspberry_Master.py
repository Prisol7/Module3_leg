import tkinter as tk
import math
# import serial
import struct
import time
import smbus
import time


class RobotDogPart:
    def __init__(self, canvas, x, y, length, angle=90, is_wheel=False, is_joint=False, label=""):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.length = length
        self.angle = angle
        self.is_wheel = is_wheel
        self.is_joint = is_joint
        self.speed = 0 if is_wheel else None
        self.id = None
        self.arrow_id = None
        self.label_id = None
        self.angle_label_id = None
        self.label = label
        self.relative_angle = 0 if is_joint else None
        self.draw()

    def draw(self):
        if self.id:
            self.canvas.delete(self.id)
        if self.arrow_id:
            self.canvas.delete(self.arrow_id)
        if self.label_id:
            self.canvas.delete(self.label_id)
        if self.angle_label_id:
            self.canvas.delete(self.angle_label_id)

        if self.is_wheel:
            self.id = self.canvas.create_oval(
                self.x - self.length, self.y - self.length,
                self.x + self.length, self.y + self.length,
                fill="gray", outline="black", tags="clickable"
            )
            arrow_angle = math.radians(self.angle)
            end_x = self.x + self.length * math.cos(arrow_angle)
            end_y = self.y + self.length * math.sin(arrow_angle)
            self.arrow_id = self.canvas.create_line(self.x, self.y, end_x, end_y, fill="red", width=3, arrow=tk.LAST, tags="clickable")
        else:
            end_x = self.x + self.length * math.cos(math.radians(self.angle))
            end_y = self.y + self.length * math.sin(math.radians(self.angle))
            self.id = self.canvas.create_line(
                self.x, self.y, end_x, end_y,
                width=8, fill="blue" if not self.is_joint else "green", tags="clickable"
            )

        if self.label:
            if self.is_wheel:
                label_x = self.x
                label_y = self.y + self.length + 20
            else:
                text_padding = 40
                mid_x = (self.x + end_x) / 2
                mid_y = (self.y + end_y) / 2
                perpendicular_x = -math.sin(math.radians(self.angle))
                perpendicular_y = math.cos(math.radians(self.angle))

                if self.is_joint:
                    label_x = mid_x + text_padding * perpendicular_x
                    label_y = mid_y + text_padding * perpendicular_y
                else:
                    label_x = mid_x - text_padding * perpendicular_x
                    label_y = mid_y - text_padding * perpendicular_y

            self.label_id = self.canvas.create_text(label_x, label_y, text=self.label, fill="black", font=("Arial", 12, "bold"))

            angle_label_y = label_y + 15
            if self.is_wheel:
                direction = "Forward" if self.speed > 0 else "Backward" if self.speed < 0 else "Stopped"
                angle_text = f"{direction}"
            else:
                display_angle = self.relative_angle if self.is_joint else self.angle
                angle_text = f"{display_angle:.1f}°"
            self.angle_label_id = self.canvas.create_text(label_x, angle_label_y, text=angle_text, fill="black", font=("Arial", 10))

    def rotate(self, angle):
        self.angle = angle
        self.draw()

    def set_speed(self, speed):
        if self.is_wheel:
            self.speed = speed
            self.draw()

    def update_relative_angle(self, leg_angle):
        if self.is_joint:
            self.relative_angle = (self.angle - leg_angle + 360) % 360
            self.rotate(leg_angle + self.relative_angle)

class RobotDogControlGUI:
    def __init__(self, master):
        self.master = master
        master.title("Robot Dog Controller")
        master.geometry("800x800")

        self.canvas = tk.Canvas(master, width=800, height=800, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.create_robot_parts()

        self.bus = smbus.SMBus(1)
        time.sleep(2)
        self.address = 0x08


        self.canvas.create_text(400, 50, text="Robot Dog Controller", font=("Arial", 24, "bold"))

        self.canvas.tag_bind("clickable", "<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.active_part = None

        #self.serial_port = "/dev/ttyACM0"
        self.baud_rate = 9600
        #self.ser = self.init_serial()

        self.is_sending = False
        self.last_send_time = 0
        self.send_interval = 0.1

        self.update_data()


    def create_robot_parts(self):
        center_x, center_y = 400, 400
        leg_spacing = 300
        wheel_spacing = 300
        leg_y = center_y - 200
        wheel_y = center_y + 200

        # Start legs (and joints) at a fixed 45° angle so the whole leg is straight on startup.
        START_LEG_ANGLE = 45

        self.parts = [
            RobotDogPart(self.canvas, center_x - leg_spacing/2, leg_y, 120, angle=START_LEG_ANGLE, label="Left Leg"),
            RobotDogPart(self.canvas, center_x - leg_spacing/2, leg_y + 120, 100, angle=START_LEG_ANGLE, is_joint=True, label="Left Joint"),
            RobotDogPart(self.canvas, center_x + leg_spacing/2, leg_y, 120, angle=START_LEG_ANGLE, label="Right Leg"),
            RobotDogPart(self.canvas, center_x + leg_spacing/2, leg_y + 120, 100, angle=START_LEG_ANGLE, is_joint=True, label="Right Joint"),
            RobotDogPart(self.canvas, center_x - wheel_spacing/2, wheel_y, 50, is_wheel=True, label="Left Wheel"),
            RobotDogPart(self.canvas, center_x + wheel_spacing/2, wheel_y, 50, is_wheel=True, label="Right Wheel")
        ]

        # Position joint endpoints to be at the end of each leg and make joint relative angles zero
        # so the joint aligns with the leg (whole leg is straight at START_LEG_ANGLE).
        # Only process the leg/joint pairs at indices 0/1 and 2/3.
        for leg_index in (0, 2):
            leg = self.parts[leg_index]
            joint = self.parts[leg_index + 1]

            # Ensure leg has the desired start angle
            leg.rotate(START_LEG_ANGLE)

            # Place the joint at the end of the leg
            joint.x = leg.x + leg.length * math.cos(math.radians(leg.angle))
            joint.y = leg.y + leg.length * math.sin(math.radians(leg.angle))

            # Keep the joint aligned with the leg (relative angle 0)
            joint.relative_angle = 0
            joint.rotate(leg.angle + joint.relative_angle)

        # Remember initial angles for non-wheel parts
        for part in self.parts:
            if not part.is_wheel:
                part.initial_angle = part.angle

    def on_press(self, event):
        clicked_items = self.canvas.find_withtag("current")
        for part in self.parts:
            if part.id in clicked_items or part.arrow_id in clicked_items:
                self.active_part = part
                self.start_x = event.x
                self.start_y = event.y
                self.is_sending = True
                break

    def on_drag(self, event):
        if self.active_part:
            dx = event.x - self.active_part.x
            dy = event.y - self.active_part.y
            new_angle = math.degrees(math.atan2(dy, dx))

            if self.active_part.is_wheel:
                self.active_part.rotate(new_angle)
                old_angle = math.degrees(math.atan2(self.start_y - self.active_part.y, self.start_x - self.active_part.x))
                angle_change = (new_angle - old_angle + 360) % 360
                speed = 1 if angle_change < 180 else -1
                self.active_part.set_speed(speed)
            else:
                if not self.active_part.is_joint:
                    angle_diff = (new_angle - self.active_part.initial_angle + 180) % 360 - 180
                    if -60 <= angle_diff <= 60:
                        self.active_part.rotate(new_angle)
                        joint_index = self.parts.index(self.active_part) + 1
                        joint = self.parts[joint_index]
                        joint.x = self.active_part.x + self.active_part.length * math.cos(math.radians(new_angle))
                        joint.y = self.active_part.y + self.active_part.length * math.sin(math.radians(new_angle))
                        joint.rotate(new_angle + joint.relative_angle)
                else:
                    leg_index = self.parts.index(self.active_part) - 1
                    leg = self.parts[leg_index]
                    relative_angle = (new_angle - leg.angle + 360) % 360
                    if 0 <= relative_angle <= 60:
                        self.active_part.relative_angle = relative_angle
                        self.active_part.rotate(leg.angle + relative_angle)

            self.start_x = event.x
            self.start_y = event.y

    def on_release(self, event):
        if self.active_part and self.active_part.is_wheel:
            self.active_part.set_speed(0)
        self.active_part = None
        self.is_sending = False

    def update_data(self):
        current_time = time.time()
        if self.is_sending and current_time - self.last_send_time >= self.send_interval:
            self.send_data()
            self.last_send_time = current_time
        self.master.after(10, self.update_data)

    def send_data(self):
        data = []
        for part in self.parts:
            if part.is_wheel:
                data.append(part.speed)
            else:
                data.append(part.angle if not part.is_joint else part.relative_angle)

        left_leg = str(int(data[0]))
        left_joint = str(int(data[1]))

        right_leg = str(int(data[2]))
        right_joint = str(int(data[3]))

        send_value = f'{left_leg:3}/{left_joint:3}/{right_leg:3}/{right_joint:3}'
        print(send_value)


        byte_data = send_value.encode('utf-8')
        #self.bus.write_byte(self.address, 32)
        self.bus.write_i2c_block_data(self.address, 0 ,list(byte_data))


if __name__ == "__main__":
    root = tk.Tk()
    gui = RobotDogControlGUI(root)
    root.mainloop()
