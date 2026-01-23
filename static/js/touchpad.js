/**
 * Touchpad Module for AirMouse
 * Encapsulates movement, scrolling, multi-touch gestures, and long-press dragging.
 */
class Touchpad {
    constructor(elementId, socket, options = {}) {
        this.pad = document.getElementById(elementId);
        if (!this.pad) return;

        this.socket = socket;
        this.getSensitivity = options.getSensitivity || (() => 4.0);
        this.feedback = options.feedback || (() => { });

        this.lx = 0; this.ly = 0; // last x, y
        this.sx = 0; this.sy = 0; // start x, y
        this.hMove = false;
        this.tCount = 0;
        this.maxTCount = 0;
        this.drag = false;
        this.longPressTimer = null;
        this.lastMultiTouchTime = 0;

        this._bindEvents();
    }

    _bindEvents() {
        this.pad.oncontextmenu = (e) => e.preventDefault();

        this.pad.addEventListener('touchstart', e => this._handleTouchStart(e));
        this.pad.addEventListener('touchmove', e => this._handleTouchMove(e), { passive: false });
        this.pad.addEventListener('touchend', e => this._handleTouchEnd(e));
        this.pad.addEventListener('touchcancel', () => this._handleTouchCancel());
    }

    _handleTouchStart(e) {
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;

        if (this.tCount === 1 && prevTCount === 0) {
            this.maxTCount = 1;
        } else {
            this.maxTCount = Math.max(this.maxTCount, this.tCount);
        }

        const touch = e.targetTouches[0];
        this.lx = touch.clientX;
        this.ly = touch.clientY;
        this.sx = this.lx;
        this.sy = this.ly;
        this.hMove = false;

        // Long press for drag (single finger)
        if (this.tCount === 1) {
            this.longPressTimer = setTimeout(() => {
                this.drag = true;
                this.socket.emit('drag_start');
                this.pad.style.background = "#001a33";
                this.feedback();
            }, 500);
        }

        // Three finger visual feedback (drag starts on move)
        if (this.tCount === 3) {
            this.pad.style.background = "#001a33";
        }
    }

    _handleTouchMove(e) {
        e.preventDefault();
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;
        this.maxTCount = Math.max(this.maxTCount, this.tCount);

        const touch = e.targetTouches[0];
        const cx = touch.clientX, cy = touch.clientY;

        // Multi-touch to single-touch lock (300ms)
        if (prevTCount >= 2 && this.tCount === 1) {
            this.lastMultiTouchTime = Date.now();
        }

        // Movement threshold
        if (Math.hypot(cx - this.sx, cy - this.sy) > 5) {
            this.hMove = true;
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }
            // Three finger drag start
            if (this.tCount === 3 && !this.drag) {
                this.drag = true;
                this.socket.emit('drag_start');
            }
        }

        const sensitivity = this.getSensitivity();

        if (this.tCount === 1 || this.tCount === 3) {
            if (Date.now() - this.lastMultiTouchTime > 300) {
                this.socket.emit('move', {
                    dx: (cx - this.lx) * sensitivity,
                    dy: (cy - this.ly) * sensitivity
                });
            }
            this.lx = cx;
            this.ly = cy;
        } else if (this.tCount === 2) {
            // 滚动时持续更新lastMultiTouchTime, 确保松手后300ms内不移动鼠标
            this.lastMultiTouchTime = Date.now();
            const dy = cy - this.ly;
            if (Math.abs(dy) > 5) {
                this.socket.emit('scroll', { dy: dy > 0 ? 1 : -1 });
                this.ly = cy;
            }
        }
    }

    _handleTouchEnd(e) {
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;

        if (prevTCount >= 2 && this.tCount === 1) {
            this.lastMultiTouchTime = Date.now();
        }

        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

        if (this.drag) {
            if (this.tCount === 0) {
                this.socket.emit('drag_end');
                this.drag = false;
                this.pad.style.background = ""; // Rely on original CSS or handle here
            }
        } else if (this.tCount === 0) {
            if (!this.hMove) {
                if (this.maxTCount === 1) this.socket.emit('click', { button: 'left' });
                else if (this.maxTCount === 2) this.socket.emit('click', { button: 'right' });
                else if (this.maxTCount === 3) this.socket.emit('click', { button: 'middle' });
            }
        }

        if (this.tCount === 0) {
            this.maxTCount = 0;
            this.pad.style.background = "";
            // If there's a global stopScroll, it should be handled outside or via callback
            if (window.stopScroll) window.stopScroll();
        }
    }

    _handleTouchCancel() {
        this.tCount = 0;
        this.maxTCount = 0;
        this.pad.style.background = "";
        if (this.drag) {
            this.socket.emit('drag_end');
            this.drag = false;
        }
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        if (window.stopScroll) window.stopScroll();
    }

    // External access to current multitouch lock
    isLocked() {
        return (Date.now() - this.lastMultiTouchTime < 300);
    }

    getLastMultiTouchTime() {
        return this.lastMultiTouchTime;
    }
}

// Export for use in scripts
window.TouchpadModule = Touchpad;
