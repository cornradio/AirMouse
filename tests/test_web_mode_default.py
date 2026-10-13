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

    def test_touchpad_page_has_home_navigation_and_mac_gesture_shortcuts(self):
        touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('aria-label="返回主页"', touchpad)
        self.assertIn('中键单击', touchpad)
        self.assertIn('快速滚动', touchpad)
        self.assertIn('切换拖拽按键', touchpad)

    def test_landscape_sensitivity_controls_are_in_a_collapsible_panel(self):
        touchpad = self.client.get('/touchpad').get_data(as_text=True)

        self.assertIn('id="sens-toggle"', touchpad)
        self.assertIn('aria-controls="sens-settings"', touchpad)
        self.assertIn('id="sens-settings"', touchpad)
        self.assertIn('function toggleSensitivityPanel()', touchpad)
        self.assertIn('id="gyro-slider"', touchpad)


if __name__ == '__main__':
    unittest.main()
