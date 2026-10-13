"""The browser interaction default follows the AirMouse server OS."""

import unittest
from unittest.mock import patch

from web_app import app, get_default_input_mode


class WebModeDefaultTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_mac_server_selects_mac_defaults_for_touchpad_and_voice(self):
        with patch('web_app.platform.system', return_value='Darwin'):
            touchpad = self.client.get('/touchpad').get_data(as_text=True)
            voice = self.client.get('/v').get_data(as_text=True)

        self.assertIn('let inputMode = "mac";', touchpad)
        self.assertIn('const defaultInputMode = "mac";', voice)
        self.assertIn("modifierKey = defaultInputMode === 'mac' ? 'meta' : 'ctrl';", voice)

    def test_windows_server_selects_windows_defaults_for_touchpad_and_voice(self):
        with patch('web_app.platform.system', return_value='Windows'):
            touchpad = self.client.get('/touchpad').get_data(as_text=True)
            voice = self.client.get('/v').get_data(as_text=True)

        self.assertIn('let inputMode = "windows";', touchpad)
        self.assertIn('const defaultInputMode = "windows";', voice)
        self.assertIn("modifierKey = defaultInputMode === 'mac' ? 'meta' : 'ctrl';", voice)

    def test_other_server_systems_fall_back_to_windows_mode(self):
        with patch('web_app.platform.system', return_value='Linux'):
            self.assertEqual(get_default_input_mode(), 'windows')
            touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('let inputMode = "windows";', touchpad)

    def test_keyboard_uses_server_default_and_exposes_mac_mode_switch(self):
        with patch('web_app.platform.system', return_value='Darwin'):
            mac_keyboard = self.client.get('/k').get_data(as_text=True)
        with patch('web_app.platform.system', return_value='Windows'):
            windows_keyboard = self.client.get('/k').get_data(as_text=True)

        self.assertIn('let keyboardMode = "mac";', mac_keyboard)
        self.assertIn('id="keyboard-mode-toggle"', mac_keyboard)
        self.assertIn('let keyboardMode = "windows";', windows_keyboard)
        self.assertIn("isMac ? '⌥' : 'ALT'", mac_keyboard)
        self.assertIn("isMac ? 'Option' : 'Alt'", mac_keyboard)
        self.assertIn('WIN', windows_keyboard)

    def test_settings_page_has_two_finger_scroll_direction_setting(self):
        settings = self.client.get('/settings').get_data(as_text=True)

        self.assertIn('id="touch-scroll-direction"', settings)
        self.assertIn('<option value="normal">正常</option>', settings)
        self.assertIn('<option value="reverse">反向</option>', settings)
        self.assertIn("localStorage.setItem('touch_scroll_direction'", settings)

    def test_touchpad_page_has_home_navigation_and_mac_gesture_shortcuts(self):
        touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('aria-label="返回主页"', touchpad)
        self.assertIn('中键单击', touchpad)
        self.assertIn('快速滚动', touchpad)
        self.assertIn('切换拖拽按键', touchpad)

    def test_touchpad_page_has_mac_system_shortcut_buttons(self):
        touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('id="mac-shortcuts"', touchpad)
        self.assertIn('调度中心', touchpad)
        self.assertIn('应用窗口', touchpad)
        self.assertIn('显示桌面', touchpad)
        self.assertIn('上一个全屏应用', touchpad)
        self.assertIn('下一个全屏应用', touchpad)
        self.assertIn("emitMacShortcut(['ctrl', 'up'])", touchpad)
        self.assertIn("emitMacShortcut(['ctrl', 'down'])", touchpad)
        self.assertIn("emitMacShortcut(['fn', 'f11'])", touchpad)
        self.assertIn("emitMacShortcut(['ctrl', 'left'])", touchpad)
        self.assertIn("emitMacShortcut(['ctrl', 'right'])", touchpad)

    def test_landscape_sensitivity_controls_are_in_a_collapsible_panel(self):
        touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('id="sens-toggle"', touchpad)
        self.assertIn('aria-controls="sens-settings"', touchpad)
        self.assertIn('id="sens-settings"', touchpad)
        self.assertIn('function toggleSensitivityPanel()', touchpad)
        self.assertIn('id="gyro-slider"', touchpad)

    def test_touchpad_has_collapsible_sensitivity_and_mac_floating_actions(self):
        touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('id="sens-toggle"', touchpad)
        self.assertIn('#mouse-page.mac-mode.mac-shortcuts-enabled #mac-floating-actions', touchpad)
        self.assertIn('aria-label="打开调度中心"', touchpad)
        self.assertIn('aria-label="显示桌面"', touchpad)
        self.assertIn("localStorage.getItem('show_mac_shortcuts')", touchpad)

    def test_settings_page_can_disable_mac_floating_actions(self):
        settings = self.client.get('/settings').get_data(as_text=True)

        self.assertIn('id="show-mac-shortcuts"', settings)
        self.assertIn("localStorage.setItem('show_mac_shortcuts'", settings)

    def test_landscape_more_menu_can_scroll_and_has_quick_scroll_button(self):
        touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('id="more-menu"', touchpad)
        self.assertIn('max-height: calc(100dvh', touchpad)
        self.assertIn('overflow-y: auto', touchpad)
        self.assertIn('touch-action: pan-y', touchpad)
        self.assertIn('html, body, #mouse-page, .top-nav, .menu-container, .menu-dropdown, .menu-dropdown *', touchpad)
        self.assertIn('.quick-scroll-up-button', touchpad)
        self.assertIn('aria-label="快速滚动向上"', touchpad)
        self.assertIn('onclick="quickScroll(4)"', touchpad)


if __name__ == '__main__':
    unittest.main()
