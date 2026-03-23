const socket = io();
const v = () => { if (navigator.vibrate) navigator.vibrate(25); };

const defaultMap = {
    btn_0: "click_left", btn_1: "click_right", btn_2: "none", btn_3: "key_esc",
    btn_4: "click_left", btn_5: "click_right", btn_6: "none", btn_7: "none",
    btn_8: "none", btn_9: "key_enter", btn_10: "none", btn_11: "none",
    btn_12: "key_up", btn_13: "key_down", btn_14: "key_left", btn_15: "key_right",
    btn_16: "none",
    stick_left: "mouse", stick_right: "scroll"
};

const MAPPING_NAMES = {
    "none": "无",
    "mouse": "光标",
    "scroll": "滚轮",
    "scroll_rev": "滚轮反向",
    "wasd": "WASD",
    "hjkl": "HJKL",
    "arrows": "方向键",
    "click_left": "左键",
    "click_right": "右键",
    "click_middle": "中键",
    "drag": "拖拽"
};

// 预处理部分预设快捷名，剩下的通过 fallback 原文大写显示
['space', 'enter', 'esc', 'backspace', 'up', 'down', 'left', 'right', 'shift', 'ctrl', 'tab', 'alt', 'win', 'delete'].forEach(k => {
    MAPPING_NAMES['key_'+k] = k.toUpperCase();
});
['w','a','s','d','e','q','r','f'].forEach(k => {
    MAPPING_NAMES['key_'+k] = k.toUpperCase();
});

let ctrlData = {
    current: "Default",
    profiles: { "Default": JSON.parse(JSON.stringify(defaultMap)) },
    sens: 5.0,
    scroll_sens: 5.0,
    deadzone: 0.15,
    curve: "medium"
};

let currentMap = ctrlData.profiles[ctrlData.current];
let currentEditKey = null;

socket.on('connect', () => {
    socket.emit('load_gp_macros');
});

socket.on('gp_macros_loaded', (data) => {
    if (data && data.profiles && Object.keys(data.profiles).length > 0) {
        ctrlData = data;
        
        // 补充缺失的默认值
        if(ctrlData.sens === undefined) ctrlData.sens = 5.0;
        if(ctrlData.scroll_sens === undefined) ctrlData.scroll_sens = 5.0;
        if(ctrlData.deadzone === undefined) ctrlData.deadzone = 0.15;
        if(ctrlData.curve === undefined) ctrlData.curve = "medium";
        if(ctrlData.enabled === undefined) ctrlData.enabled = true;
        if(!ctrlData.profiles[ctrlData.current]) {
            ctrlData.current = Object.keys(ctrlData.profiles)[0];
        }
        
    } else {
        // 服务端无数据时使用全新初始化数据
        ctrlData = {
            current: "Default",
            profiles: { "Default": JSON.parse(JSON.stringify(defaultMap)) },
            sens: 5.0,
            scroll_sens: 5.0,
            deadzone: 0.15,
            enabled: true
        };
        saveToServer();
    }
    
    currentMap = ctrlData.profiles[ctrlData.current];
    document.getElementById('gp-status').innerText = '🟢 设置已同步至电脑';
    document.getElementById('gp-status').classList.add('connected');
    
    initUI();
    updateMasterSwitch();
    updateUIValues();
});

function toggleMapping() {
    ctrlData.enabled = (ctrlData.enabled === false) ? true : false;
    updateMasterSwitch();
    saveToServer();
};

function refreshGamepads() {
    socket.emit('get_gamepads');
}

function selectGamepad(index) {
    socket.emit('select_gamepad', parseInt(index));
}

socket.on('gamepads_list', (list) => {
    const sel = document.getElementById('gp-select');
    if(!sel) return;
    sel.innerHTML = '';
    if(list.length === 0) {
        sel.innerHTML = '<option value="0">未发现设备</option>';
    } else {
        list.forEach(gp => {
            const opt = document.createElement('option');
            opt.value = gp.index;
            opt.innerText = gp.name;
            sel.appendChild(opt);
        });
    }
});

socket.on('gp_status', (data) => {
    const statusEl = document.getElementById('gp-status');
    if(!statusEl) return;
    if(data.connected) {
        statusEl.innerHTML = `<span style="color:#00ff00">🟢 已连接: ${data.name}</span>`;
    } else {
        statusEl.innerHTML = `<span style="color:#ff3b30">🔴 ${data.name || "等待连接"}</span>`;
    }
});

// 初始刷新一次设备列表
setTimeout(refreshGamepads, 1000);

function updateMasterSwitch() {
    const sw = document.getElementById('master-switch-btn');
    if(ctrlData.enabled !== false) {
        sw.className = 'master-switch active';
        sw.innerText = '手柄映射状态: 开启 ✅';
    } else {
        sw.className = 'master-switch';
        sw.innerText = '手柄映射状态: 暂停 ⏸️';
    }
}

function saveToServer() {
    socket.emit('save_gp_macros', ctrlData);
    document.getElementById('gp-status').innerText = '🟢 已保存至电脑';
}

function initUI() {
    // 监听设置
    const sensInput = document.getElementById('param-sens');
    const sensVal = document.getElementById('sens-val');
    sensInput.value = ctrlData.sens || 5.0;
    sensVal.innerText = (ctrlData.sens || 5.0).toFixed(1);

    sensInput.onchange = (e) => {
        ctrlData.sens = parseFloat(e.target.value);
        sensVal.innerText = ctrlData.sens.toFixed(1);
        saveToServer();
    };

    const curveSelect = document.getElementById('param-curve');
    curveSelect.value = ctrlData.curve || 'medium';
    curveSelect.onchange = (e) => {
        ctrlData.curve = e.target.value;
        saveToServer();
    };

    const scrollSensInput = document.getElementById('param-scroll-sens');
    scrollSensInput.value = ctrlData.scroll_sens || 10;
    scrollSensInput.onchange = (e) => {
        ctrlData.scroll_sens = parseFloat(e.target.value);
        saveToServer();
    };

    const deadInput = document.getElementById('param-deadzone');
    deadInput.value = ctrlData.deadzone || 0.15;
    deadInput.onchange = (e) => {
        ctrlData.deadzone = parseFloat(e.target.value);
        saveToServer();
    };

    updateProfileList();

    // 点击外部关弹窗
    window.onclick = function(event) {
        if (event.target.classList.contains('modal-outer')) {
            closeEdit();
        }
    }
}

// 刷新界面上显示的名称
function updateUIValues() {
    for (let key in currentMap) {
        const el = document.getElementById(`val-${key}`);
        if (el) {
            let val = currentMap[key];
            let display = MAPPING_NAMES[val] || val;
            
            if (val.includes('+')) {
                const keys = val.split('+');
                display = keys.map(k => MAPPING_NAMES[k] || k.replace('key_', '').toUpperCase()).join('+');
                MAPPING_NAMES[val] = display;
            }
            
            el.innerText = display;
            
            // 核心：通过 class 统一控制外观，不仅好看也方便调试
            el.classList.toggle('is-none', val === 'none');
            // 清理可能残留的内联样式
            el.style.color = '';
            el.style.background = '';
        }
    }
}

// === Profiles (多套配置) ===
function updateProfileList() {
    const listEl = document.getElementById('profile-list');
    if(!listEl) return;
    listEl.innerHTML = '';
    
    for (let p in ctrlData.profiles) {
        const item = document.createElement('div');
        item.className = 'profile-item' + (p === ctrlData.current ? ' active' : '');
        item.onclick = (e) => {
            if(e.target.classList.contains('action-btn')) return;
            v(); switchProfile(p);
        };

        const nameSpan = document.createElement('span');
        nameSpan.innerText = p;
        item.appendChild(nameSpan);

        const actions = document.createElement('div');
        actions.className = 'item-actions';

        const editBtn = document.createElement('span');
        editBtn.className = 'action-btn'; editBtn.innerText = '✏️';
        editBtn.onclick = () => renameProfile(p);
        actions.appendChild(editBtn);

        const delBtn = document.createElement('span');
        delBtn.className = 'action-btn'; delBtn.innerText = '🗑️';
        delBtn.style.color = '#ff3b30';
        delBtn.onclick = () => deleteProfile(p);
        actions.appendChild(delBtn);

        item.appendChild(actions);
        listEl.appendChild(item);
    }
}

function switchProfile(name) {
    if (!ctrlData.profiles[name]) return;
    ctrlData.current = name;
    currentMap = ctrlData.profiles[name];
    saveToServer();
    updateUIValues();
    updateProfileList(); // 刷新高亮
}

function renameProfile(oldName) {
    const newName = prompt("重命名配置:", oldName);
    if (!newName || newName === oldName) return;
    if (ctrlData.profiles[newName]) { alert("该名称已存在！"); return; }
    
    ctrlData.profiles[newName] = ctrlData.profiles[oldName];
    delete ctrlData.profiles[oldName];
    
    if (ctrlData.current === oldName) {
        ctrlData.current = newName;
    }
    
    saveToServer();
    updateProfileList();
}

function addProfile() {
    const name = prompt("新建配置名称:");
    if (name && !ctrlData.profiles[name]) {
        ctrlData.profiles[name] = JSON.parse(JSON.stringify(currentMap)); 
        switchProfile(name);
        updateProfileList();
    } else if (name) {
        alert("名称已存在！");
    }
}

function deleteProfile(name) {
    if (Object.keys(ctrlData.profiles).length <= 1) {
        alert("至少需要保留一个配置！");
        return;
    }
    if (!confirm(`确定要删除配置 "${name}" 吗？`)) return;
    
    delete ctrlData.profiles[name];
    if (ctrlData.current === name) {
        ctrlData.current = Object.keys(ctrlData.profiles)[0];
        currentMap = ctrlData.profiles[ctrlData.current];
    }
    
    saveToServer();
    updateUIValues();
    updateProfileList();
}

// === 编辑 Modal ===
function openEdit(keyId, title) {
    v();
    currentEditKey = keyId;
    document.getElementById('vkb-title').innerText = "配置: " + title;
    
    const isStick = keyId.startsWith('stick_');
    document.getElementById('stick-presets-area').style.display = isStick ? 'flex' : 'none';
    document.getElementById('vk-grid').style.display = isStick ? 'none' : 'flex';
    
    const isDPad = ['btn_12', 'btn_13', 'btn_14', 'btn_15'].includes(keyId);
    const isABXY = ['btn_0', 'btn_1', 'btn_2', 'btn_3'].includes(keyId);
    if(isDPad || isABXY) {
        document.getElementById('quick-presets-area').style.display = 'flex';
        document.getElementById('quick-preset-title').innerText = isDPad ? '💡 快速填充整个十字键组:' : '💡 快速填充整个 ABXY 键组:';
    } else {
        document.getElementById('quick-presets-area').style.display = 'none';
    }
    
    document.getElementById('combo-mode-bar').style.display = isStick ? 'none' : 'flex';
    document.getElementById('combo-toggle').checked = false;
    toggleComboMode(false);
    
    document.getElementById('manual-key-input').value = '';
    document.getElementById('key-help-panel').style.display = 'none';
    document.getElementById('vkb-modal').style.display = 'flex';
}

function closeEdit() {
    document.getElementById('vkb-modal').style.display = 'none';
}

function assignBulk(type) {
    if(!currentEditKey) return;
    
    // 十字键组
    if (['btn_12', 'btn_13', 'btn_14', 'btn_15'].includes(currentEditKey)) {
        if(type === 'arrows') {
            currentMap['btn_12'] = 'key_up'; currentMap['btn_13'] = 'key_down';
            currentMap['btn_14'] = 'key_left'; currentMap['btn_15'] = 'key_right';
        }
        if(type === 'wasd') {
            currentMap['btn_12'] = 'key_w'; currentMap['btn_13'] = 'key_s';
            currentMap['btn_14'] = 'key_a'; currentMap['btn_15'] = 'key_d';
        }
    }
    // ABXY组 (Y=3, A=0, X=2, B=1)
    if (['btn_0', 'btn_1', 'btn_2', 'btn_3'].includes(currentEditKey)) {
        if(type === 'arrows') {
            currentMap['btn_3'] = 'key_up'; currentMap['btn_0'] = 'key_down';
            currentMap['btn_2'] = 'key_left'; currentMap['btn_1'] = 'key_right';
        }
        if(type === 'wasd') {
            currentMap['btn_3'] = 'key_w'; currentMap['btn_0'] = 'key_s';
            currentMap['btn_2'] = 'key_a'; currentMap['btn_1'] = 'key_d';
        }
    }
    v();
    document.getElementById('vkb-modal').style.display = 'none';
    saveToServer();
    updateUIValues();
}

let isComboMode = false;
let currentCombo = [];

function toggleComboMode(checked) {
    isComboMode = checked;
    currentCombo = [];
    document.getElementById('combo-display').style.display = checked ? 'block' : 'none';
    document.getElementById('combo-confirm-btn').style.display = checked ? 'block' : 'none';
    document.getElementById('combo-clear-btn').style.display = checked ? 'block' : 'none';
    document.getElementById('combo-display').innerText = '...等待按下组合...';
}

function clearCombo() {
    currentCombo = [];
    document.getElementById('combo-display').innerText = '...等待按下组合...';
}

function confirmCombo() {
    v();
    if (currentCombo.length === 0) return;
    const combinedVal = currentCombo.join('+');
    currentMap[currentEditKey] = combinedVal;
    
    const displayNames = currentCombo.map(k => MAPPING_NAMES[k] || k.replace('key_', '').toUpperCase());
    MAPPING_NAMES[combinedVal] = displayNames.join(' + ');
    
    document.getElementById('vkb-modal').style.display = 'none';
    saveToServer();
    updateUIValues();
}

// 手动输入按键绑定
function assignManualKey() {
    const inputEl = document.getElementById('manual-key-input');
    const val = inputEl.value.trim().toLowerCase();
    if (!val) return;
    assignVKey(val);
    inputEl.value = '';
}

function toggleKeyHelp() {
    const el = document.getElementById('key-help-panel');
    el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}

// 虚拟键盘直接绑定回调
function assignVKey(key) {
    if(!currentEditKey) return;
    
    if (isComboMode) {
        if (['none', 'click_left', 'click_right', 'click_middle', 'mouse', 'scroll', 'scroll_rev', 'wasd', 'hjkl', 'arrows'].includes(key)) {
            alert('此功能不可用于组合键拼装！仅限常规键盘按键。');
            return;
        }
        const mappedVal = 'key_' + key;
        if (!currentCombo.includes(mappedVal)) {
            currentCombo.push(mappedVal);
        }
        const displayNames = currentCombo.map(k => MAPPING_NAMES[k] || k.replace('key_', '').toUpperCase());
        document.getElementById('combo-display').innerText = displayNames.join(' + ');
        return; // 不直接退出弹窗
    }
    
    let mappedVal = key;
    if (key !== 'none' && !key.startsWith('click_') && !key.startsWith('scroll') && key !== 'mouse' && key !== 'wasd' && key !== 'arrows' && key !== 'hjkl') {
        mappedVal = 'key_' + key;
    }
    
    currentMap[currentEditKey] = mappedVal;
    
    document.getElementById('vkb-modal').style.display = 'none';
    saveToServer();
    updateUIValues();
}

// === 可视化 UI 动效反馈 ===
function updateGamepadUI() {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : (navigator.webkitGetGamepads ? navigator.webkitGetGamepads() : []);
    let activePad = null;
    for (let i = 0; i < gamepads.length; i++) {
        if (gamepads[i] && gamepads[i].connected) {
            activePad = gamepads[i]; break;
        }
    }

    if (activePad) {
        // 更新按键按下状态 (蓝色高亮)
        activePad.buttons.forEach((btn, idx) => {
            const valSpan = document.getElementById(`val-btn_${idx}`);
            if (valSpan) {
                const parent = valSpan.parentElement;
                if (btn.pressed) {
                    parent.style.transform = 'scale(0.85)';
                    parent.style.boxShadow = '0 0 10px #007AFF, inset 0 0 10px #007AFF';
                    parent.style.borderColor = '#007AFF';
                    parent.style.zIndex = '100';
                } else {
                    parent.style.transform = '';
                    parent.style.boxShadow = '';
                    parent.style.borderColor = '';
                    parent.style.zIndex = '';
                }
            }
        });

        // 动画摇杆位置
        const l_x = activePad.axes[0] || 0, l_y = activePad.axes[1] || 0;
        const r_x = activePad.axes[2] || 0, r_y = activePad.axes[3] || 0;
        
        const stickL = document.querySelector('.gb-ls');
        if (stickL) stickL.style.transform = `translate(${l_x * 20}px, ${l_y * 15}px)`;
        
        const stickR = document.querySelector('.gb-rs');
        if (stickR) stickR.style.transform = `translate(${r_x * 20}px, ${r_y * 15}px)`;
    }

    requestAnimationFrame(updateGamepadUI);
}
requestAnimationFrame(updateGamepadUI);
