"""Regression checks for macOS key-code and text event handling."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import keyboard_service


class KeyboardServiceMacTests(unittest.TestCase):
    def test_function_key_uses_macos_virtual_key_code(self):
        special_keys = keyboard_service.get_special_keys()
        self.assertEqual(keyboard_service._resolve_keycode(special_keys['f1']), 122)

    def test_fn_key_uses_macos_virtual_key_code_and_is_a_modifier(self):
        self.assertEqual(keyboard_service._resolve_keycode('fn'), 63)
        self.assertTrue(keyboard_service._is_modifier('fn'))

    def test_unknown_key_does_not_fall_through_to_keycode_zero(self):
        self.assertIsNone(keyboard_service._resolve_keycode('not-a-real-key'))

    def test_text_events_preserve_case_and_unicode_and_are_released(self):
        created = []
        unicode_strings = []
        posted = []
        released = []

        def create_event(_source, keycode, key_down):
            event = len(created) + 1
            created.append((event, keycode, key_down))
            return event

        quartz = SimpleNamespace(
            CGEventCreateKeyboardEvent=create_event,
            CGEventKeyboardSetUnicodeString=lambda event, length, value: unicode_strings.append(
                (event, length, tuple(value))
            ),
            CGEventPost=lambda _tap, event: posted.append(event),
        )
        with patch.object(keyboard_service, '_quartz', quartz), patch.object(
            keyboard_service, '_release_event', side_effect=released.append
        ):
            keyboard_service._mac_type_text('A中😀')

        self.assertEqual([entry[2] for entry in created], [True, False] * 3)
        self.assertEqual([entry[1] for entry in created], [0] * 6)
        self.assertEqual(
            [entry[1:] for entry in unicode_strings],
            [(1, (65,)), (1, (65,)), (1, (20013,)), (1, (20013,)),
             (2, (55357, 56832)), (2, (55357, 56832))],
        )
        self.assertEqual(posted, [1, 2, 3, 4, 5, 6])
        self.assertEqual(released, [1, 2, 3, 4, 5, 6])

    def test_cancelled_repeat_worker_does_not_press_after_key_up(self):
        presses = []
        releases = []
        workers = []

        class DeferredThread:
            def __init__(self, target, args, daemon):
                self.target = target
                self.args = args

            def start(self):
                workers.append(self)

        with patch.object(keyboard_service, 'get_special_keys', return_value={}), patch.object(
            keyboard_service, '_mac_key_down', side_effect=presses.append
        ), patch.object(keyboard_service, '_mac_key_up', side_effect=releases.append), patch.object(
            keyboard_service.threading, 'Thread', DeferredThread
        ):
            keyboard_service.handle_key_action({'key': 'a', 'action': 'down'})
            keyboard_service.handle_key_action({'key': 'a', 'action': 'up'})
            workers[0].target(*workers[0].args)

        self.assertEqual(presses, ['a'])  # The synchronous initial down only.
        self.assertEqual(releases, ['a'])
        self.assertNotIn('a', keyboard_service.active_repeats)

    def test_repeat_worker_marks_subsequent_key_down_as_autorepeat(self):
        class StopAfterOneRepeat:
            def __init__(self):
                self.wait_calls = 0

            def wait(self, _delay):
                self.wait_calls += 1
                return self.wait_calls == 2

            def is_set(self):
                return False

        stop_event = StopAfterOneRepeat()
        keyboard_service.active_repeats['a'] = stop_event
        try:
            with patch.object(keyboard_service, '_mac_key_down') as key_down:
                keyboard_service._repeat_key('a', stop_event, 'a')
            key_down.assert_called_once_with('a', autorepeat=True)
        finally:
            keyboard_service.active_repeats.pop('a', None)


if __name__ == '__main__':
    unittest.main()
