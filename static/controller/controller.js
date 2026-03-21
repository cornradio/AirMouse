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
    "mouse": "鼠标",
    "scroll": "滚轮",
    "wasd": "WASD",
    "hjkl": "HJKL",
    "arrows": "方向键",
    "click_left": "左键",
    "click_right": "右键",
    "click_middle": "中键",
    "drag": "拖拽",
    "key_space": "空格",
    "key_enter": "回车",
    "key_esc": "ESC",
    "key_backspace": "退格",
    "key_w":"W", "key_a":"A", "key_s":"S", "key_d":"D",
    "key_e":"E", "key_q":"Q", "key_r":"R", "key_f":"F",
    "key_shift": "Shift", "key_ctrl":"Ctrl", "key_tab":"Tab",
    "key_up": "↑", "key_down": "↓", "key_left": "←", "key_right": "→"
};

let ctrlData = {
    current: "Default",
    profiles: { "Default": JSON.parse(JSON.stringify(defaultMap)) },
    sens: 5.0,
    deadzone: 0.15
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
        if(!ctrlData.sens) ctrlData.sens = 5.0;
        if(!ctrlData.deadzone) ctrlData.deadzone = 0.15;
        if(!ctrlData.profiles[ctrlData.current]) {
            ctrlData.current = Object.keys(ctrlData.profiles)[0];
        }
        
    } else {
        // 服务端无数据时使用全新初始化数据
        ctrlData = {
            current: "Default",
            profiles: { "Default": JSON.parse(JSON.stringify(defaultMap)) },
            sens: 5.0,
            deadzone: 0.15
        };
        saveToServer();
    }
    
    currentMap = ctrlData.profiles[ctrlData.current];
    document.getElementById('gp-status').innerText = '🟢 设置已同步至电脑';
    document.getElementById('gp-status').classList.add('connected');
    
    initUI();
    updateUIValues();
});

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

    const deadInput = document.getElementById('param-deadzone');
    const deadVal = document.getElementById('dead-val');
    deadInput.value = ctrlData.deadzone || 0.15;
    deadVal.innerText = (ctrlData.deadzone || 0.15).toFixed(2);

    deadInput.onchange = (e) => {
        ctrlData.deadzone = parseFloat(e.target.value);
        deadVal.innerText = ctrlData.deadzone.toFixed(2);
        saveToServer();
    };

    updateProfileSelect();

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
            el.innerText = MAPPING_NAMES[currentMap[key]] || currentMap[key];
        }
    }
}

// === Profiles (多套配置) ===
function updateProfileSelect() {
    const sel = document.getElementById('profile-select');
    sel.innerHTML = '';
    for (let p in ctrlData.profiles) {
        const opt = document.createElement('option');
        opt.value = p; opt.innerText = p;
        if (p === ctrlData.current) opt.selected = true;
        sel.appendChild(opt);
    }
}

function switchProfile(name) {
    if (!ctrlData.profiles[name]) return;
    ctrlData.current = name;
    currentMap = ctrlData.profiles[name];
    saveToServer();
    updateUIValues();
}

function addProfile() {
    const name = prompt("新建配置名称:");
    if (name && !ctrlData.profiles[name]) {
        ctrlData.profiles[name] = JSON.parse(JSON.stringify(currentMap)); 
        switchProfile(name);
        updateProfileSelect();
    } else if (name) {
        alert("名称已存在！");
    }
}

function deleteProfile() {
    if (Object.keys(ctrlData.profiles).length <= 1) {
        alert("至少需要保留一个配置！");
        return;
    }
    if (confirm(`删除配置 "${ctrlData.current}"?`)) {
        delete ctrlData.profiles[ctrlData.current];
        switchProfile(Object.keys(ctrlData.profiles)[0]);
        updateProfileSelect();
    }
}

// === 编辑 Modal ===
function openEdit(keyId, title) {
    v();
    currentEditKey = keyId;
    document.getElementById('edit-title').innerText = "配置: " + title;
    
    if (keyId.startsWith('stick_')) {
        document.getElementById('btn-options').style.display = 'none';
        document.getElementById('stick-options').style.display = 'block';
        document.getElementById('stick-select').value = currentMap[keyId] || 'none';
    } else {
        document.getElementById('btn-options').style.display = 'block';
        document.getElementById('stick-options').style.display = 'none';
        document.getElementById('btn-select').value = currentMap[keyId] || 'none';
    }
    
    document.getElementById('edit-modal').style.display = 'flex';
}

function closeEdit() {
    document.getElementById('edit-modal').style.display = 'none';
}

function saveEdit() {
    const val = currentEditKey.startsWith('stick_') 
        ? document.getElementById('stick-select').value 
        : document.getElementById('btn-select').value;
    
    currentMap[currentEditKey] = val;
    saveToServer();
    updateUIValues();
    closeEdit();
}
