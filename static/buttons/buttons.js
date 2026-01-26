const socket = io();
let audioCtx = null;
function initAudio() { if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
const v = () => { if (navigator.vibrate) navigator.vibrate(25); };

let editMode = false;
let sortMode = false;
let currentEditIndex = -1;
let currentProfile = "Default";
let sortInst = null;

let macroData = {
    current: "Default",
    profiles: { "Default": { cols: 4, buttons: Array(16).fill(null).map(() => ({ label: "", emoji: "", keys: "" })) } }
};

// --- Data Sync ---
socket.emit('load_macros');
socket.on('macros_loaded', (data) => {
    if (data && data.profiles) {
        macroData = data;
        currentProfile = macroData.current || Object.keys(macroData.profiles)[0] || "Default";
    }
    updateProfileUI();
    renderButtons();
});

function saveToServer() { socket.emit('save_macros', macroData); }

function updateProfileUI() {
    const select = document.getElementById('profile-select');
    if (!select) return;
    select.innerHTML = '';
    Object.keys(macroData.profiles).forEach(name => {
        const opt = document.createElement('option');
        opt.value = name; opt.innerText = name;
        if (name === currentProfile) opt.selected = true;
        select.appendChild(opt);
    });
}

function switchProfile(name) {
    currentProfile = name;
    macroData.current = name;
    saveToServer();
    renderButtons();
}

function addProfile() {
    const name = prompt("New Profile Name:");
    if (name && !macroData.profiles[name]) {
        macroData.profiles[name] = { cols: 4, buttons: Array(16).fill(null).map(() => ({ label: "", emoji: "", keys: "" })) };
        currentProfile = name;
        macroData.current = name;
        updateProfileUI(); saveToServer(); renderButtons();
    }
}

function duplicateProfile() {
    const newName = prompt(`Copy current profile "${currentProfile}" to:`);
    if (newName && !macroData.profiles[newName]) {
        // 深拷贝当前配置
        macroData.profiles[newName] = JSON.parse(JSON.stringify(macroData.profiles[currentProfile]));
        currentProfile = newName;
        macroData.current = newName;
        updateProfileUI(); saveToServer(); renderButtons();
    } else if (newName) {
        alert("Profile name already exists!");
    }
}

// --- Render ---
function renderButtons() {
    const grid = document.getElementById('btn-grid');
    if (!grid) return;
    grid.innerHTML = '';
    const profile = macroData.profiles[currentProfile];
    grid.style.setProperty('--cols', profile.cols);

    // 根据列数设置固定字体大小，避免横竖屏切换时的计算偏差
    let eSize = '32px', lSize = '13px';
    if (profile.cols == 3) { eSize = '42px'; lSize = '16px'; }
    else if (profile.cols == 5) { eSize = '24px'; lSize = '11px'; }
    grid.style.setProperty('--emoji-fs', eSize);
    grid.style.setProperty('--label-fs', lSize);

    profile.buttons.forEach((cfg, i) => {
        const btn = document.createElement('div');
        btn.className = 'macro-btn';
        if (editMode) btn.classList.add('editing');
        if (sortMode) btn.classList.add('sorting');

        if (cfg.emoji) {
            const em = document.createElement('div');
            em.className = 'emoji'; em.innerText = cfg.emoji;
            btn.appendChild(em);
        }
        if (cfg.label) {
            const label = document.createElement('div');
            label.className = 'label'; label.innerText = cfg.label;
            btn.appendChild(label);
        }

        // Interactions
        if (!editMode && !sortMode) {
            btn.onpointerdown = () => handleBtnDown(i);
            btn.onpointerup = () => handleBtnUp(i);
            btn.onpointercancel = () => handleBtnUp(i);
        } else if (editMode) {
            btn.onclick = () => { v(); openBtnConfig(i); };
        }

        grid.appendChild(btn);
    });

    initSortable();
}

// --- Sorting ---
function initSortable() {
    const grid = document.getElementById('btn-grid');
    if (!grid) return;

    if (sortInst) {
        sortInst.destroy();
        sortInst = null;
    }

    if (!sortMode) return;

    if (typeof Sortable === 'undefined') {
        console.error("[Sort] ERROR: Sortable library is NOT defined in global scope.");
        return;
    }

    try {
        sortInst = new Sortable(grid, {
            animation: 200,
            swap: true,
            swapClass: 'sortable-swap-highlight',
            ghostClass: 'sortable-ghost',
            forceFallback: true,
            onStart: function () { v(); },
            onEnd: function (evt) {
                if (evt.oldIndex === undefined || evt.newIndex === undefined || evt.oldIndex === evt.newIndex) return;

                const btns = macroData.profiles[currentProfile].buttons;
                const temp = btns[evt.oldIndex];
                btns[evt.oldIndex] = btns[evt.newIndex];
                btns[evt.newIndex] = temp;

                saveToServer();
                setTimeout(() => { renderButtons(); }, 50);
            }
        });
    } catch (err) {
        console.error("[Sort] Exception during Sortable creation:", err);
    }
}

// --- Mode Toggles ---
function toggleEditMode() {
    v();
    editMode = !editMode;
    if (editMode) sortMode = false;
    updateHeaderUI();
    renderButtons();
}

function toggleSortMode() {
    v();
    sortMode = !sortMode;
    if (sortMode) editMode = false;
    updateHeaderUI();
    renderButtons();
}

function updateHeaderUI() {
    const editToggle = document.getElementById('edit-toggle');
    const sortToggle = document.getElementById('sort-toggle');
    if (editToggle) editToggle.classList.toggle('active', editMode);
    if (sortToggle) sortToggle.classList.toggle('active', sortMode);
}

// --- Handlers ---
function handleBtnDown(i) {
    initAudio(); v();
    const cfg = macroData.profiles[currentProfile].buttons[i];
    if (cfg && cfg.keys) {
        const keyList = cfg.keys.split(',').map(k => k.trim().toLowerCase()).filter(k => k);
        if (keyList.length > 1) {
            socket.emit('key_combo', { keys: keyList });
        } else if (keyList.length === 1) {
            socket.emit('key_action', { key: keyList[0], action: 'down' });
        }
    }
}

function handleBtnUp(i) {
    const cfg = macroData.profiles[currentProfile].buttons[i];
    if (cfg && cfg.keys) {
        const keyList = cfg.keys.split(',').map(k => k.trim().toLowerCase()).filter(k => k);
        if (keyList.length === 1) {
            socket.emit('key_action', { key: keyList[0], action: 'up' });
        }
    }
}

// --- Config ---
function showProfileConfig() {
    const cfgGrid = document.getElementById('cfg-grid-size');
    if (cfgGrid) cfgGrid.value = macroData.profiles[currentProfile].cols;
    const modal = document.getElementById('profile-modal');
    if (modal) modal.style.display = 'flex';
}
function closeProfileConfig() {
    const modal = document.getElementById('profile-modal');
    if (modal) modal.style.display = 'none';
}

function saveProfileConfig() {
    const newCols = parseInt(document.getElementById('cfg-grid-size').value);
    const profile = macroData.profiles[currentProfile];
    const target = newCols * newCols;
    if (profile.buttons.length > target && !confirm(`This will truncate extra buttons. OK?`)) return;

    profile.cols = newCols;
    if (profile.buttons.length < target) {
        while (profile.buttons.length < target) profile.buttons.push({ label: "", emoji: "", keys: "" });
    } else {
        profile.buttons = profile.buttons.slice(0, target);
    }
    saveToServer(); closeProfileConfig(); renderButtons();
}

function deleteCurrentProfile() {
    if (Object.keys(macroData.profiles).length <= 1) return;
    if (confirm(`Delete current profile?`)) {
        delete macroData.profiles[currentProfile];
        currentProfile = Object.keys(macroData.profiles)[0];
        macroData.current = currentProfile;
        updateProfileUI(); saveToServer(); closeProfileConfig(); renderButtons();
    }
}

function deleteCurrentButton() {
    if (confirm("Permanently clear this button's data?")) {
        macroData.profiles[currentProfile].buttons[currentEditIndex] = { label: "", emoji: "", keys: "" };
        saveToServer();
        closeBtnConfig();
        renderButtons();
    }
}

function openBtnConfig(i) {
    currentEditIndex = i;
    const cfg = macroData.profiles[currentProfile].buttons[i];
    document.getElementById('cfg-label').value = cfg.label || '';
    document.getElementById('cfg-emoji').value = cfg.emoji || '';
    document.getElementById('cfg-keys').value = cfg.keys || '';
    document.getElementById('btn-modal').style.display = 'flex';
}
function closeBtnConfig() { document.getElementById('btn-modal').style.display = 'none'; }
function saveBtnConfig() {
    macroData.profiles[currentProfile].buttons[currentEditIndex] = {
        label: document.getElementById('cfg-label').value.trim(),
        emoji: document.getElementById('cfg-emoji').value.trim(),
        keys: document.getElementById('cfg-keys').value.trim()
    };
    saveToServer(); closeBtnConfig(); renderButtons();
}

async function toggleFullScreen() {
    const doc = document.documentElement;
    try {
        if (!document.fullscreenElement && !document.webkitFullscreenElement) {
            if (doc.requestFullscreen) {
                await doc.requestFullscreen();
            } else if (doc.webkitRequestFullscreen) {
                await doc.webkitRequestFullscreen();
            } else {
                alert("iOS Safari 不支持 JS 触发全屏。请点击 Safari 菜单中的 '添加到主屏幕' 以获得全屏体验。");
            }
        } else {
            if (document.exitFullscreen) {
                await document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                await document.webkitExitFullscreen();
            }
        }
    } catch (err) {
        console.warn("Fullscreen failed:", err);
    }
}

// --- Initialize Touchpad ---
document.addEventListener('DOMContentLoaded', () => {
    const touchpad = new TouchpadModule('pad-area', socket, {
        getSensitivity: () => parseFloat(localStorage.getItem('mouse_sense')) || 4.0,
        feedback: v
    });

    // 点击外部取消弹窗 logic
    window.onclick = function (event) {
        if (event.target.classList.contains('modal-outer')) {
            closeBtnConfig();
            closeProfileConfig();
        }
    }
});
