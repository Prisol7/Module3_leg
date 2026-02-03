/**
 * Robot Controls - WebSocket communication and UI handlers
 */

class RobotController {
    constructor() {
        this.socket = null;
        this.canvas = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.init();
    }

    init() {
        // Initialize canvas with callback for drag events
        this.canvas = new RobotCanvas('robot-canvas', (side, part, angle) => {
            this.handleCanvasDrag(side, part, angle);
        });

        this.connectSocket();
        this.setupSliders();
        this.setupButtons();
    }

    handleCanvasDrag(side, part, angle) {
        // Update slider and display
        const sliderId = `${side}-${part}-slider`;
        const valueId = `${side}-${part}-value`;

        document.getElementById(sliderId).value = angle;
        document.getElementById(valueId).textContent = `${angle.toFixed(1)}°`;

        // Emit to server
        if (this.socket && this.socket.connected) {
            const eventName = part === 'leg' ? 'set_leg' : 'set_joint';
            this.socket.emit(eventName, { side: side, angle: angle });
        }
    }

    connectSocket() {
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000
        });

        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.setConnectionStatus(true);
            this.reconnectAttempts = 0;
            this.socket.emit('get_status');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.setConnectionStatus(false);
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.reconnectAttempts++;
        });

        this.socket.on('state_update', (state) => {
            this.updateUI(state);
            this.canvas.render(state);
        });

        this.socket.on('error', (data) => {
            console.error('Server error:', data.message);
            this.showToast(data.message, 'error');
        });
    }

    setConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (connected) {
            statusEl.textContent = 'Connected';
            statusEl.className = 'connected';
        } else {
            statusEl.textContent = 'Disconnected';
            statusEl.className = 'disconnected';
        }
    }

    setupSliders() {
        const getCurrentState = () => ({
            left_leg: { angle: parseFloat(document.getElementById('left-leg-slider').value) },
            right_leg: { angle: parseFloat(document.getElementById('right-leg-slider').value) },
            left_joint: { angle: parseFloat(document.getElementById('left-joint-slider').value) },
            right_joint: { angle: parseFloat(document.getElementById('right-joint-slider').value) }
        });

        const leftLegSlider = document.getElementById('left-leg-slider');
        leftLegSlider.addEventListener('input', (e) => {
            const angle = parseFloat(e.target.value);
            document.getElementById('left-leg-value').textContent = `${angle.toFixed(1)}°`;
            const state = getCurrentState();
            state.left_leg.angle = angle;
            this.canvas.render(state);
            this.socket.emit('set_leg', { side: 'left', angle: angle });
        });

        const rightLegSlider = document.getElementById('right-leg-slider');
        rightLegSlider.addEventListener('input', (e) => {
            const angle = parseFloat(e.target.value);
            document.getElementById('right-leg-value').textContent = `${angle.toFixed(1)}°`;
            const state = getCurrentState();
            state.right_leg.angle = angle;
            this.canvas.render(state);
            this.socket.emit('set_leg', { side: 'right', angle: angle });
        });

        const leftJointSlider = document.getElementById('left-joint-slider');
        leftJointSlider.addEventListener('input', (e) => {
            const angle = parseFloat(e.target.value);
            document.getElementById('left-joint-value').textContent = `${angle.toFixed(1)}°`;
            const state = getCurrentState();
            state.left_joint.angle = angle;
            this.canvas.render(state);
            this.socket.emit('set_joint', { side: 'left', angle: angle });
        });

        const rightJointSlider = document.getElementById('right-joint-slider');
        rightJointSlider.addEventListener('input', (e) => {
            const angle = parseFloat(e.target.value);
            document.getElementById('right-joint-value').textContent = `${angle.toFixed(1)}°`;
            const state = getCurrentState();
            state.right_joint.angle = angle;
            this.canvas.render(state);
            this.socket.emit('set_joint', { side: 'right', angle: angle });
        });
    }

    setupButtons() {
        const sendBtn = document.getElementById('send-btn');
        sendBtn.addEventListener('click', () => {
            this.socket.emit('send_now');
            this.showToast('Data sent!', 'success');
        });

        sendBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.socket.emit('send_now');
            this.showToast('Data sent!', 'success');
        });
    }

    updateUI(state) {
        document.getElementById('left-leg-slider').value = state.left_leg.angle;
        document.getElementById('left-leg-value').textContent = `${state.left_leg.angle.toFixed(1)}°`;
        document.getElementById('right-leg-slider').value = state.right_leg.angle;
        document.getElementById('right-leg-value').textContent = `${state.right_leg.angle.toFixed(1)}°`;
        document.getElementById('left-joint-slider').value = state.left_joint.angle;
        document.getElementById('left-joint-value').textContent = `${state.left_joint.angle.toFixed(1)}°`;
        document.getElementById('right-joint-slider').value = state.right_joint.angle;
        document.getElementById('right-joint-value').textContent = `${state.right_joint.angle.toFixed(1)}°`;
    }

    showToast(message, type = 'info') {
        let toast = document.getElementById('toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast';
            document.body.appendChild(toast);
        }
        const colors = { success: '#4CAF50', error: '#f44336', info: '#2196F3' };
        toast.style.background = colors[type] || colors.info;
        toast.textContent = message;
        toast.style.opacity = '1';
        setTimeout(() => { toast.style.opacity = '0'; }, 2000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.robotController = new RobotController();
});
