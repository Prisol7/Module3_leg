#!/usr/bin/env python3
"""
Flask web application for Robot Dog Controller.
Provides WebSocket-based real-time control interface.
"""

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'robot-dog-controller-2024'

# Use eventlet for async WebSocket handling if available, otherwise threading
try:
    import eventlet
    eventlet.monkey_patch()
    async_mode = 'eventlet'
except ImportError:
    async_mode = 'threading'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

# Import robot controller
from robot_controller import RobotController
robot = RobotController(i2c_addr=0x08, bus_num=1)


class SendThrottle:
    """Rate limiter for I2C sends (100ms interval like original)."""

    def __init__(self, interval=0.1):
        self.interval = interval
        self.last_send = 0
        self.lock = threading.Lock()

    def should_send(self):
        with self.lock:
            now = time.time()
            if now - self.last_send >= self.interval:
                self.last_send = now
                return True
            return False


throttle = SendThrottle()


# ============== HTTP Routes ==============

@app.route('/')
def index():
    """Serve the main control interface."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """REST endpoint for current robot state."""
    return jsonify(robot.get_state_dict())


@app.route('/api/health')
def api_health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'i2c_available': robot.bus is not None,
        'async_mode': async_mode
    })


# ============== WebSocket Events ==============

@socketio.on('connect')
def handle_connect():
    """Handle client connection - send current state."""
    logger.info('Client connected')
    emit('state_update', robot.get_state_dict())


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')


@socketio.on('get_status')
def handle_get_status():
    """Client requests current state."""
    emit('state_update', robot.get_state_dict())


@socketio.on('set_leg')
def handle_set_leg(data):
    """
    Handle leg angle update.
    Expects: {side: 'left'|'right', angle: float}
    """
    side = data.get('side')
    angle = data.get('angle')

    if side not in ('left', 'right') or angle is None:
        emit('error', {'message': 'Invalid leg data'})
        return

    success, msg = robot.set_leg(side, angle)

    if success and throttle.should_send():
        robot.send_data_safe()

    # Broadcast updated state to all clients
    emit('state_update', robot.get_state_dict(), broadcast=True)


@socketio.on('set_joint')
def handle_set_joint(data):
    """
    Handle joint angle update.
    Expects: {side: 'left'|'right', angle: float}
    """
    side = data.get('side')
    angle = data.get('angle')

    if side not in ('left', 'right') or angle is None:
        emit('error', {'message': 'Invalid joint data'})
        return

    success, msg = robot.set_joint(side, angle)

    if success and throttle.should_send():
        robot.send_data_safe()

    # Broadcast updated state to all clients
    emit('state_update', robot.get_state_dict(), broadcast=True)


@socketio.on('send_now')
def handle_send_now():
    """Force immediate I2C send."""
    robot.send_data_safe()
    emit('state_update', robot.get_state_dict(), broadcast=True)


# ============== Main ==============

if __name__ == '__main__':
    logger.info('Starting Robot Dog Controller Web Server')
    logger.info(f'Async mode: {async_mode}')
    logger.info('Access at http://0.0.0.0:5000')
    logger.info('In AP mode: http://192.168.4.1:5000')

    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
