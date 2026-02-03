/**
 * Robot Canvas - Visual representation with drag-to-control
 */

class RobotCanvas {
    constructor(canvasId, onAngleChange) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.onAngleChange = onAngleChange;

        this.centerX = 300;
        this.topY = 80;
        this.legSpacing = 250;
        this.legLength = 90;
        this.jointLength = 70;

        this.colors = {
            leg: '#2196F3',
            joint: '#4CAF50',
            pivot: '#FF9800',
            label: '#ffffff',
            labelBg: 'rgba(0, 0, 0, 0.5)'
        };

        this.state = {
            left_leg: { angle: 45 },
            left_joint: { angle: 0 },
            right_leg: { angle: 45 },
            right_joint: { angle: 0 }
        };

        // Dragging state
        this.isDragging = false;
        this.dragTarget = null; // { side: 'left'|'right', part: 'leg'|'joint' }
        this.dragThreshold = 20; // pixels to grab handle

        this.setupEvents();
        this.render(this.state);
    }

    setupEvents() {
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.handleStart(e));
        window.addEventListener('mousemove', (e) => this.handleMove(e));
        window.addEventListener('mouseup', () => this.handleEnd());

        // Touch events
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.handleStart(e.touches[0]);
        }, { passive: false });

        window.addEventListener('touchmove', (e) => {
            if (this.isDragging) e.preventDefault();
            this.handleMove(e.touches[0]);
        }, { passive: false });

        window.addEventListener('touchend', () => this.handleEnd());

        // Cursor feedback
        this.canvas.addEventListener('mousemove', (e) => this.updateCursor(e));
    }

    getMousePos(evt) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        return {
            x: (evt.clientX - rect.left) * scaleX,
            y: (evt.clientY - rect.top) * scaleY
        };
    }

    distance(p1, p2) {
        return Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);
    }

    getLegGeometry(side) {
        const pivotX = side === 'left'
            ? this.centerX - this.legSpacing / 2
            : this.centerX + this.legSpacing / 2;
        const pivotY = this.topY;

        const legAngle = this.state[`${side}_leg`].angle * Math.PI / 180;
        const jointAngle = (this.state[`${side}_leg`].angle + this.state[`${side}_joint`].angle) * Math.PI / 180;

        const kneeX = pivotX + this.legLength * Math.cos(legAngle);
        const kneeY = pivotY + this.legLength * Math.sin(legAngle);

        const footX = kneeX + this.jointLength * Math.cos(jointAngle);
        const footY = kneeY + this.jointLength * Math.sin(jointAngle);

        return {
            pivot: { x: pivotX, y: pivotY },
            knee: { x: kneeX, y: kneeY },
            foot: { x: footX, y: footY }
        };
    }

    checkHit(pos) {
        // Check legs (pivot points)
        for (const side of ['left', 'right']) {
            const geom = this.getLegGeometry(side);
            if (this.distance(pos, geom.pivot) < this.dragThreshold) {
                return { side, part: 'leg', center: geom.pivot };
            }
            if (this.distance(pos, geom.knee) < this.dragThreshold) {
                return { side, part: 'joint', center: geom.knee };
            }
        }
        return null;
    }

    updateCursor(e) {
        if (this.isDragging) return;
        const pos = this.getMousePos(e);
        const hit = this.checkHit(pos);
        this.canvas.style.cursor = hit ? 'grab' : 'crosshair';
    }

    handleStart(e) {
        const pos = this.getMousePos(e);
        const hit = this.checkHit(pos);

        if (hit) {
            this.isDragging = true;
            this.dragTarget = hit;
            this.canvas.classList.add('dragging');
            this.canvas.style.cursor = 'grabbing';
        }
    }

    handleMove(e) {
        if (!this.isDragging || !this.dragTarget) return;

        const pos = this.getMousePos(e);
        const { side, part, center } = this.dragTarget;

        let angle;
        if (part === 'leg') {
            // Calculate angle from pivot to mouse
            const dx = pos.x - center.x;
            const dy = pos.y - center.y;
            angle = Math.atan2(dy, dx) * 180 / Math.PI;
            // Clamp to valid range
            angle = Math.max(-15, Math.min(105, angle));
        } else {
            // For joint, calculate relative to leg angle
            const dx = pos.x - center.x;
            const dy = pos.y - center.y;
            const absoluteAngle = Math.atan2(dy, dx) * 180 / Math.PI;
            const legAngle = this.state[`${side}_leg`].angle;
            angle = absoluteAngle - legAngle;
            // Clamp to valid range [0, 60]
            angle = Math.max(0, Math.min(60, angle));
        }

        // Update state
        this.state[`${side}_${part}`].angle = angle;

        // Notify controller
        if (this.onAngleChange) {
            this.onAngleChange(side, part, angle);
        }

        this.render(this.state);
    }

    handleEnd() {
        this.isDragging = false;
        this.dragTarget = null;
        this.canvas.classList.remove('dragging');
        this.canvas.style.cursor = 'crosshair';
    }

    render(state) {
        this.state = state;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawGrid();

        this.ctx.fillStyle = this.colors.label;
        this.ctx.font = 'bold 16px Segoe UI';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('Robot Leg Visualization', this.centerX, 30);

        this.drawLeg('left', state.left_leg.angle, state.left_joint.angle);
        this.drawLeg('right', state.right_leg.angle, state.right_joint.angle);

        // Draw drag handles highlight if not dragging
        if (!this.isDragging) {
            this.drawHandles();
        }
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        this.ctx.lineWidth = 1;
        for (let x = 0; x <= this.canvas.width; x += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        for (let y = 0; y <= this.canvas.height; y += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    drawHandles() {
        // Draw subtle rings around draggable points
        for (const side of ['left', 'right']) {
            const geom = this.getLegGeometry(side);

            // Pivot handle
            this.ctx.beginPath();
            this.ctx.strokeStyle = 'rgba(255, 152, 0, 0.3)';
            this.ctx.lineWidth = 2;
            this.ctx.arc(geom.pivot.x, geom.pivot.y, this.dragThreshold, 0, 2 * Math.PI);
            this.ctx.stroke();

            // Knee handle
            this.ctx.beginPath();
            this.ctx.strokeStyle = 'rgba(76, 175, 80, 0.3)';
            this.ctx.arc(geom.knee.x, geom.knee.y, this.dragThreshold, 0, 2 * Math.PI);
            this.ctx.stroke();
        }
    }

    drawLeg(side, legAngle, jointRelativeAngle) {
        const geom = this.getLegGeometry(side);

        // Draw leg
        this.ctx.beginPath();
        this.ctx.strokeStyle = this.colors.leg;
        this.ctx.lineWidth = 8;
        this.ctx.lineCap = 'round';
        this.ctx.moveTo(geom.pivot.x, geom.pivot.y);
        this.ctx.lineTo(geom.knee.x, geom.knee.y);
        this.ctx.stroke();

        // Draw pivot
        this.ctx.beginPath();
        this.ctx.fillStyle = this.colors.pivot;
        this.ctx.arc(geom.pivot.x, geom.pivot.y, 8, 0, 2 * Math.PI);
        this.ctx.fill();

        // Draw knee
        this.ctx.beginPath();
        this.ctx.fillStyle = this.colors.joint;
        this.ctx.arc(geom.knee.x, geom.knee.y, 6, 0, 2 * Math.PI);
        this.ctx.fill();

        // Draw joint
        this.ctx.beginPath();
        this.ctx.strokeStyle = this.colors.joint;
        this.ctx.lineWidth = 6;
        this.ctx.lineCap = 'round';
        this.ctx.moveTo(geom.knee.x, geom.knee.y);
        this.ctx.lineTo(geom.foot.x, geom.foot.y);
        this.ctx.stroke();

        // Draw foot
        this.ctx.beginPath();
        this.ctx.fillStyle = '#888';
        this.ctx.arc(geom.foot.x, geom.foot.y, 5, 0, 2 * Math.PI);
        this.ctx.fill();

        // Labels
        const labelSide = side === 'left' ? -1 : 1;
        this.drawLabel(geom.pivot.x + (labelSide * 60), geom.pivot.y - 10,
            `${side.charAt(0).toUpperCase() + side.slice(1)} Leg`, `${legAngle.toFixed(1)}°`);
        this.drawLabel(geom.knee.x + (labelSide * 50), geom.knee.y + 20,
            'Joint', `${jointRelativeAngle.toFixed(1)}° rel`);
    }

    drawLabel(x, y, title, value) {
        this.ctx.font = 'bold 11px Segoe UI';
        this.ctx.textAlign = 'center';
        const titleWidth = this.ctx.measureText(title).width;
        const valueWidth = this.ctx.measureText(value).width;
        const width = Math.max(titleWidth, valueWidth) + 16;
        this.ctx.fillStyle = this.colors.labelBg;
        this.ctx.beginPath();
        this.ctx.roundRect(x - width/2, y - 10, width, 36, 4);
        this.ctx.fill();
        this.ctx.fillStyle = this.colors.label;
        this.ctx.fillText(title, x, y + 5);
        this.ctx.fillStyle = '#FF9800';
        this.ctx.font = '12px Segoe UI';
        this.ctx.fillText(value, x, y + 20);
    }
}

// Export for use in controls.js
window.RobotCanvas = RobotCanvas;
