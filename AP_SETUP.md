# Raspberry Pi Access Point Setup Guide

This guide explains how to configure your Raspberry Pi as a WiFi Access Point so you can connect directly to it and control the robot dog via the web interface.

## Overview

When configured as an Access Point, the Pi will:
- Create a WiFi network (e.g., "RobotDog")
- Assign IP addresses to connected devices
- Serve the web controller at `http://192.168.4.1:5000`

---

## Prerequisites

- Raspberry Pi with built-in WiFi (Pi 3, Pi 4, Pi Zero W)
- Raspberry Pi OS (Bullseye or newer recommended)
- SSH or direct terminal access

---

## Step 1: Update the System

```bash
sudo apt update
sudo apt upgrade -y
```

---

## Step 2: Install Required Packages

```bash
sudo apt install hostapd dnsmasq -y
```

- **hostapd**: Creates the WiFi Access Point
- **dnsmasq**: Provides DHCP (assigns IP addresses to connected devices)

---

## Step 3: Stop Services During Configuration

```bash
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
```

---

## Step 4: Configure Static IP for wlan0

Edit the dhcpcd configuration:

```bash
sudo nano /etc/dhcpcd.conf
```

Add these lines at the end:

```
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
```

Save and exit (Ctrl+X, Y, Enter).

---

## Step 5: Configure DHCP Server (dnsmasq)

Backup the original config and create a new one:

```bash
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
sudo nano /etc/dnsmasq.conf
```

Add these lines:

```
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/robot.local/192.168.4.1
```

This configuration:
- Uses wlan0 for DHCP
- Assigns IPs from 192.168.4.2 to 192.168.4.20
- Leases last 24 hours
- Optionally maps `robot.local` to the Pi

Save and exit.

---

## Step 6: Configure Access Point (hostapd)

Create the hostapd configuration:

```bash
sudo nano /etc/hostapd/hostapd.conf
```

Add these lines (customize SSID and password):

```
country_code=US
interface=wlan0
ssid=RobotDog
hw_mode=g
channel=7
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=robotdog123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

**Important settings:**
- `ssid`: Your network name (change "RobotDog" to your preference)
- `wpa_passphrase`: Your WiFi password (minimum 8 characters)
- `channel`: WiFi channel (1-11 for US, 7 is usually good)
- `country_code`: Your country code (US, GB, DE, etc.)

Save and exit.

Tell hostapd where to find the config:

```bash
sudo nano /etc/default/hostapd
```

Find the line `#DAEMON_CONF=""` and change it to:

```
DAEMON_CONF="/etc/hostapd/hostapd.conf"
```

Save and exit.

---

## Step 7: Enable and Start Services

```bash
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
```

Reboot to apply changes:

```bash
sudo reboot
```

---

## Step 8: Verify the Access Point

After reboot, check if the AP is running:

```bash
sudo systemctl status hostapd
sudo systemctl status dnsmasq
```

Both should show "active (running)".

You should now see "RobotDog" (or your chosen SSID) in available WiFi networks.

---

## Step 9: Install Python Dependencies

```bash
cd /path/to/Module3_leg
pip3 install -r requirements.txt
```

Or install manually:

```bash
pip3 install flask flask-socketio eventlet
```

---

## Step 10: Run the Web Server

### Manual Start (for testing)

```bash
cd /path/to/Module3_leg
python3 app.py
```

You should see:
```
Starting Robot Dog Controller Web Server
Async mode: eventlet
Access at http://0.0.0.0:5000
In AP mode: http://192.168.4.1:5000
```

### Auto-Start on Boot (systemd service)

Create a service file:

```bash
sudo nano /etc/systemd/system/robotdog.service
```

Add these lines (adjust paths as needed):

```ini
[Unit]
Description=Robot Dog Web Controller
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/Module3_leg/app.py
WorkingDirectory=/home/pi/Module3_leg
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable robotdog.service
sudo systemctl start robotdog.service
```

Check status:

```bash
sudo systemctl status robotdog.service
```

---

## Usage

1. **Connect to the Pi's WiFi:**
   - Network: `RobotDog` (or your SSID)
   - Password: `robotdog123` (or your password)

2. **Open a web browser and go to:**
   ```
   http://192.168.4.1:5000
   ```

3. **Control the robot:**
   - Use the sliders to adjust leg and joint angles
   - The canvas shows a live visualization
   - Click "Send Now" to force immediate transmission

---

## Troubleshooting

### Can't see the WiFi network

Check hostapd status and logs:

```bash
sudo systemctl status hostapd
sudo journalctl -u hostapd -n 50
```

Common issues:
- Country code not set (required on newer Pi OS)
- WiFi already connected to another network (disable in wpa_supplicant)

### Can't connect to the network

Check dnsmasq:

```bash
sudo systemctl status dnsmasq
sudo journalctl -u dnsmasq -n 50
```

### Web page won't load

1. Check if the server is running:
   ```bash
   sudo systemctl status robotdog.service
   ```

2. Check the server logs:
   ```bash
   sudo journalctl -u robotdog.service -n 50
   ```

3. Test locally on the Pi:
   ```bash
   curl http://localhost:5000
   ```

### I2C errors

1. Ensure I2C is enabled:
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > I2C > Yes
   ```

2. Check if Teensy is detected:
   ```bash
   i2cdetect -y 1
   ```
   You should see `08` in the output grid.

---

## Network Diagram

```
┌─────────────────────────────────────┐
│           Raspberry Pi              │
│                                     │
│   ┌─────────────┐  ┌─────────────┐  │
│   │   hostapd   │  │   Flask     │  │
│   │  (WiFi AP)  │  │  (Web UI)   │  │
│   │             │  │  Port 5000  │  │
│   └──────┬──────┘  └──────┬──────┘  │
│          │                │         │
│          │         ┌──────┴──────┐  │
│          │         │   smbus     │  │
│          │         │   (I2C)     │  │
│          │         └──────┬──────┘  │
└──────────┼────────────────┼─────────┘
           │                │
    ┌──────┴──────┐   ┌─────┴─────┐
    │   Phone/    │   │   Teensy  │
    │   Laptop    │   │  (Servos) │
    └─────────────┘   └───────────┘
```

---

## Quick Reference

| Item | Value |
|------|-------|
| Pi IP Address | 192.168.4.1 |
| Web Interface | http://192.168.4.1:5000 |
| Default SSID | RobotDog |
| Default Password | robotdog123 |
| I2C Address | 0x08 |
| I2C Bus | 1 |

---

## Files Created

| File | Purpose |
|------|---------|
| `app.py` | Flask web server |
| `robot_controller.py` | I2C communication |
| `templates/index.html` | Web interface |
| `static/css/style.css` | Dark theme styling |
| `static/js/robot-canvas.js` | Visual representation |
| `static/js/controls.js` | WebSocket handlers |
| `requirements.txt` | Python dependencies |
