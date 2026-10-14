/**
 * Touchpad Module for AirMouse
 * Encapsulates movement, scrolling, multi-touch gestures, and long-press dragging.
 *
 * Gesture mapping:
 *   1 finger     → mouse move / left click
 *   2 fingers    → scroll (2x speed)
 *   3 fingers    → drag / middle click
 *   4 fingers    → fast scroll (4x speed)
 */
class Touchpad {
    constructor(elementId, socket, options = {}) {
        this.pad = document.getElementById(elementId);
        if (!this.pad) return;

        this.socket = socket;
        this.getSensitivity = options.getSensitivity || (() => 4.0);
        this.feedback = options.feedback || (() => { });
        this.getMode = options.getMode || (() => 'windows');
        this.getScrollDirection = options.getScrollDirection || (() => 'normal');
        this.now = options.now || (() => Date.now());
        this.requestFrame = options.requestFrame || (callback => requestAnimationFrame(callback));
        this.cancelFrame = options.cancelFrame || (id => cancelAnimationFrame(id));

        this.lx = 0; this.ly = 0;
        this.sx = 0; this.sy = 0;
        this.hMove = false;
        this.tCount = 0;
        this.maxTCount = 0;
        this.drag = false;
        this.longPressTimer = null;
        this.lastMultiTouchTime = 0;
        this.scrollX = 0;
        this.scrollY = 0;
        this.scrollVelocityX = 0;
        this.scrollVelocityY = 0;
        this.lastScrollAt = 0;
        this.momentumFrame = null;

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
        // 新手势开始时取消尚未完成的惯性，避免两个手势的滚动叠加。
        this._cancelMomentum();
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;

        // 第二根手指落下后不再允许单指长按计时器启动拖拽。
        if (this.tCount !== 1 && this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

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
        if (this.tCount >= 2) {
            const center = this._touchCenter(e.targetTouches);
            this.lx = center.x;
            this.ly = center.y;
            this.sx = center.x;
            this.sy = center.y;
            this.scrollX = 0;
            this.scrollY = 0;
            this.scrollVelocityX = 0;
            this.scrollVelocityY = 0;
            this.lastScrollAt = this.now();
        }
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

        // Visual feedback for 3+ finger gestures
        if (this.tCount >= 3) {
            this.pad.style.background = "#001a33";
        }
    }

    _handleTouchMove(e) {
        e.preventDefault();
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;
        this.maxTCount = Math.max(this.maxTCount, this.tCount);

        // 多指手势统一以触点组中心追踪，确保起点和后续增量使用同一坐标系。
        const touch = e.targetTouches[0];
        // 触点对象字段是 clientX/clientY；_touchCenter 返回的字段则是 x/y。
        const point = this.tCount >= 2
            ? this._touchCenter(e.targetTouches)
            : { x: touch.clientX, y: touch.clientY };
        const cx = point.x, cy = point.y;
        // 有些浏览器/传感器会给出缺失坐标；避免 NaN 经 Socket.IO 序列化成 null。
        if (!Number.isFinite(cx) || !Number.isFinite(cy)) return;

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
            // 1-finger: move mouse; 3-finger: drag (already in progress)
            // 三指拖拽本身就是多指操作，不应被“多指后防止光标跳变”的单指锁延迟。
            if (this.tCount === 3 || this.now() - this.lastMultiTouchTime > 300) {
                const dx = (cx - this.lx) * sensitivity;
                const dy = (cy - this.ly) * sensitivity;
                if (!Number.isFinite(dx) || !Number.isFinite(dy)) return;
                this.socket.emit('move', {
                    dx,
                    dy
                });
            }
            this.lx = cx;
            this.ly = cy;
        } else if (this.tCount === 2) {
            const center = this._touchCenter(e.targetTouches);
            // 在原始触摸增量处翻转方向，让离手后的惯性也继承同一方向。
            const direction = this.getScrollDirection() === 'reverse' ? -1 : 1;
            const dx = (center.x - this.lx) * direction;
            const dy = (center.y - this.ly) * direction;
            this.lastMultiTouchTime = this.now();
            if (this.getMode() === 'mac') {
                // Mac 模式发送像素级增量，并按触摸速度计算抬手后的惯性。
                const at = this.now();
                const elapsed = Math.max(1, at - this.lastScrollAt);
                // 用时间常数平滑采样速度，兼容 60/120Hz 屏幕，并在停顿后快速归零。
                const blend = 1 - Math.exp(-elapsed / 45);
                this.scrollVelocityX = this.scrollVelocityX * (1 - blend) + dx / elapsed * blend;
                this.scrollVelocityY = this.scrollVelocityY * (1 - blend) + dy / elapsed * blend;
                this.lastScrollAt = at;
                if (dx || dy) this.socket.emit('scroll', { dx, dy, smooth: true });
            } else {
                // Windows 使用标准滚轮档位；累计小幅移动，避免轻微抖动触发滚动。
                this.scrollX += dx;
                this.scrollY += dy;
                const threshold = 24;
                const wheelX = Math.trunc(this.scrollX / threshold);
                const wheelY = Math.trunc(this.scrollY / threshold);
                if (wheelX || wheelY) {
                    this.socket.emit('scroll', { dx: wheelX, dy: wheelY });
                    this.scrollX -= wheelX * threshold;
                    this.scrollY -= wheelY * threshold;
                }
            }
            this.lx = center.x;
            this.ly = center.y;
        } else if (this.tCount === 4) {
            // 四指快速滚动基于整个触点组的中心位移，避免首指偏离中心造成反向跳动。
            this.lastMultiTouchTime = this.now();
            const dy = cy - this.ly;
            if (Math.abs(dy) > 3) {
                this.socket.emit('scroll', { dy: dy > 0 ? 2 : -2, speed: 4 });
                this.ly = cy;
            }
        }
    }

    _handleTouchEnd(e) {
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;

        if (prevTCount === 2 && this.tCount === 0 && this.getMode() === 'mac') {
            this._startMomentum();
        }

        if (prevTCount >= 2 && this.tCount <= 1) {
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
                this.pad.style.background = "";
            }
        } else if (this.tCount === 0) {
            if (!this.hMove) {
                if (this.maxTCount === 1) this.socket.emit('click', { button: 'left' });
                else if (this.maxTCount === 2) this.socket.emit('click', { button: 'right' });
                else if (this.maxTCount === 3) this.socket.emit('click', { button: 'middle' });
                else if (this.maxTCount === 4) this.socket.emit('click', { button: 'x1' });
            }
        }

        if (this.tCount === 0) {
            this.maxTCount = 0;
            this.pad.style.background = "";
            if (window.stopScroll) window.stopScroll();
        }
    }

    _handleTouchCancel() {
        this._cancelMomentum();
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

    _touchCenter(touches) {
        let x = 0, y = 0;
        for (let i = 0; i < touches.length; i++) {
            x += touches[i].clientX;
            y += touches[i].clientY;
        }
        return { x: x / touches.length, y: y / touches.length };
    }

    _cancelMomentum() {
        if (this.momentumFrame !== null) this.cancelFrame(this.momentumFrame);
        this.momentumFrame = null;
    }

    _startMomentum() {
        if (Math.hypot(this.scrollVelocityX, this.scrollVelocityY) < 0.015) return;
        let previousAt = this.now();
        const tick = at => {
            const elapsed = Math.min(32, Math.max(1, at - previousAt));
            previousAt = at;
            // Mac 触控板抬手后会继续滑行；约半秒的时间常数保留自然惯性。
            const decay = Math.exp(-elapsed / 480);
            this.scrollVelocityX *= decay;
            this.scrollVelocityY *= decay;
            if (Math.hypot(this.scrollVelocityX, this.scrollVelocityY) < 0.015) {
                this.momentumFrame = null;
                return;
            }
            this.socket.emit('scroll', {
                dx: this.scrollVelocityX * elapsed,
                dy: this.scrollVelocityY * elapsed,
                smooth: true
            });
            this.momentumFrame = this.requestFrame(tick);
        };
        this.momentumFrame = this.requestFrame(tick);
    }

    isLocked() {
        return (Date.now() - this.lastMultiTouchTime < 300);
    }

    getLastMultiTouchTime() {
        return this.lastMultiTouchTime;
    }
}

window.TouchpadModule = Touchpad;
