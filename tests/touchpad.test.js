const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createTouchpad(mode, scrollDirection = 'normal') {
    let now = 0;
    let nextFrameId = 1;
    const frames = new Map();
    const handlers = {};
    const events = [];
    const clearedTimers = [];
    const pad = {
        style: {},
        addEventListener(name, handler) { handlers[name] = handler; }
    };
    const context = {
        document: { getElementById: () => pad },
        window: { stopScroll() {} },
        Date: { now: () => now },
        setTimeout: () => 1,
        clearTimeout(id) { clearedTimers.push(id); },
        requestAnimationFrame(callback) {
            const id = nextFrameId++;
            frames.set(id, callback);
            return id;
        },
        cancelAnimationFrame(id) { frames.delete(id); },
        Math,
    };
    vm.runInNewContext(
        fs.readFileSync(path.join(__dirname, '../static/js/touchpad.js'), 'utf8'),
        context
    );
    const touchpad = new context.window.TouchpadModule('pad', {
        emit: (name, data) => events.push({ name, data })
    }, { getMode: () => mode, getScrollDirection: () => scrollDirection, now: () => now });

    const finger = (x, y) => ({ clientX: x, clientY: y });
    return {
        events, frames, clearedTimers, touchpad,
        setTime(value) { now = value; },
        start(touches) { handlers.touchstart({ targetTouches: touches }); },
        move(touches) { handlers.touchmove({ targetTouches: touches, preventDefault() {} }); },
        end(touches = []) { handlers.touchend({ targetTouches: touches }); },
        finger,
        flushFrame(id, at) {
            const callback = frames.get(id);
            frames.delete(id);
            now = at;
            callback?.(at);
        }
    };
}

test('Mac mode sends smooth two-finger deltas and momentum after lift', () => {
    const pad = createTouchpad('mac');
    pad.start([pad.finger(40, 50), pad.finger(60, 50)]);
    pad.setTime(20);
    pad.move([pad.finger(40, 70), pad.finger(60, 70)]);

    assert.deepEqual(JSON.parse(JSON.stringify(pad.events[0])), {
        name: 'scroll', data: { dx: 0, dy: 20, smooth: true }
    });

    pad.end();
    assert.equal(pad.frames.size, 1);
    const firstFrame = [...pad.frames.keys()][0];
    pad.flushFrame(firstFrame, 36);
    assert.equal(pad.events.length, 2);
    assert.equal(pad.events[1].data.smooth, true);
    assert.ok(pad.events[1].data.dy > 0 && pad.events[1].data.dy < 20);
});

test('Windows mode converts two-finger motion to wheel steps without momentum', () => {
    const pad = createTouchpad('windows');
    pad.start([pad.finger(40, 50), pad.finger(60, 50)]);
    pad.setTime(20);
    pad.move([pad.finger(40, 60), pad.finger(60, 60)]);
    assert.equal(pad.events.length, 0);

    pad.setTime(40);
    pad.move([pad.finger(40, 80), pad.finger(60, 80)]);
    assert.deepEqual(JSON.parse(JSON.stringify(pad.events)), [{ name: 'scroll', data: { dx: 0, dy: 1 } }]);

    pad.end();
    assert.equal(pad.frames.size, 0);
});

test('reverse direction inverts smooth Mac two-finger scrolling and momentum', () => {
    const pad = createTouchpad('mac', 'reverse');
    pad.start([pad.finger(40, 50), pad.finger(60, 50)]);
    pad.setTime(20);
    pad.move([pad.finger(40, 70), pad.finger(60, 70)]);

    assert.deepEqual(JSON.parse(JSON.stringify(pad.events[0])), {
        name: 'scroll', data: { dx: 0, dy: -20, smooth: true }
    });

    pad.end();
    const firstFrame = [...pad.frames.keys()][0];
    pad.flushFrame(firstFrame, 36);
    assert.ok(pad.events[1].data.dy < 0);
});

test('reverse direction inverts Windows two-finger wheel steps', () => {
    const pad = createTouchpad('windows', 'reverse');
    pad.start([pad.finger(40, 50), pad.finger(60, 50)]);
    pad.setTime(20);
    pad.move([pad.finger(40, 80), pad.finger(60, 80)]);

    assert.deepEqual(JSON.parse(JSON.stringify(pad.events)), [
        { name: 'scroll', data: { dx: 0, dy: -1 } }
    ]);
});

test('a new touch cancels pending Mac momentum', () => {
    const pad = createTouchpad('mac');
    pad.start([pad.finger(40, 50), pad.finger(60, 50)]);
    pad.setTime(20);
    pad.move([pad.finger(40, 75), pad.finger(60, 75)]);
    pad.end();
    const pendingFrame = [...pad.frames.keys()][0];

    pad.start([pad.finger(50, 90)]);
    pad.flushFrame(pendingFrame, 36);
    assert.equal(pad.events.length, 1);
    assert.equal(pad.frames.size, 0);
});

test('a pause before lifting a Mac scroll gesture does not leave stale momentum', () => {
    const pad = createTouchpad('mac');
    pad.start([pad.finger(40, 50), pad.finger(60, 50)]);
    pad.setTime(20);
    pad.move([pad.finger(40, 70), pad.finger(60, 70)]);
    pad.setTime(500);
    pad.move([pad.finger(40, 70), pad.finger(60, 70)]);
    pad.end();

    assert.equal(pad.frames.size, 0);
});

test('adding a second finger cancels the single-finger long-press timer', () => {
    const pad = createTouchpad('mac');
    pad.start([pad.finger(40, 50)]);
    pad.start([pad.finger(40, 50), pad.finger(60, 50)]);

    assert.deepEqual(pad.clearedTimers, [1]);
    assert.equal(pad.touchpad.longPressTimer, null);
});

test('four-finger fast scroll follows the moving touch group, not the first-finger offset', () => {
    const pad = createTouchpad('mac');
    pad.start([
        pad.finger(20, 100), pad.finger(40, 200),
        pad.finger(60, 300), pad.finger(80, 400)
    ]);
    pad.setTime(20);
    pad.move([
        pad.finger(20, 110), pad.finger(40, 210),
        pad.finger(60, 310), pad.finger(80, 410)
    ]);

    assert.deepEqual(JSON.parse(JSON.stringify(pad.events)), [
        { name: 'scroll', data: { dy: 2, speed: 4 } }
    ]);
});

test('three-finger tap emits a middle-click action', () => {
    const pad = createTouchpad('mac');
    pad.start([pad.finger(20, 20), pad.finger(40, 20), pad.finger(60, 20)]);
    pad.end();

    assert.deepEqual(JSON.parse(JSON.stringify(pad.events)), [
        { name: 'click', data: { button: 'middle' } }
    ]);
});

test('three-finger drag keeps moving immediately after a recent scroll gesture', () => {
    const pad = createTouchpad('windows');
    pad.start([pad.finger(20, 20), pad.finger(40, 20)]);
    pad.setTime(24);
    pad.move([pad.finger(20, 50), pad.finger(40, 50)]);
    pad.end();

    pad.setTime(40);
    pad.start([pad.finger(20, 20), pad.finger(40, 20), pad.finger(60, 20)]);
    pad.setTime(60);
    pad.move([pad.finger(30, 30), pad.finger(50, 30), pad.finger(70, 30)]);

    assert.deepEqual(JSON.parse(JSON.stringify(pad.events.slice(-2))), [
        { name: 'drag_start' },
        { name: 'move', data: { dx: 40, dy: 40 } }
    ]);
});

test('touchpad drops movement samples with invalid coordinates', () => {
    const pad = createTouchpad('mac');
    pad.start([pad.finger(20, 20)]);
    pad.setTime(1000);
    pad.move([{ clientX: undefined, clientY: 30 }]);

    assert.deepEqual(pad.events, []);
});

test('single-finger movement still emits finite pointer deltas', () => {
    const pad = createTouchpad('mac');
    pad.start([pad.finger(20, 20)]);
    pad.setTime(1000);
    pad.move([pad.finger(22, 25)]);

    assert.deepEqual(JSON.parse(JSON.stringify(pad.events)), [
        { name: 'move', data: { dx: 8, dy: 20 } }
    ]);
});
