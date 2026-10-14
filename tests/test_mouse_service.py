"""Regression checks for mouse event dispatch and scroll direction."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import mouse_service


class MouseServiceMacTests(unittest.TestCase):
    def test_click_posts_down_then_up_at_same_cursor_position(self):
        events = []
        with patch.object(mouse_service, '_get_pos', return_value=(10.0, 20.0)), patch.object(
            mouse_service, '_post_mouse_event', side_effect=lambda *args: events.append(args)
        ), patch.object(mouse_service.time, 'sleep'):
            mouse_service.handle_click({'button': 'right'})

        self.assertEqual(events, [(3, 1, 10.0, 20.0), (4, 1, 10.0, 20.0)])

    def test_side_buttons_use_other_mouse_events_and_distinct_button_ids(self):
        events = []
        with patch.object(mouse_service, '_get_pos', return_value=(10.0, 20.0)), patch.object(
            mouse_service, '_post_mouse_event', side_effect=lambda *args: events.append(args)
        ), patch.object(mouse_service.time, 'sleep'):
            mouse_service.handle_click({'button': 'x1'})
            mouse_service.handle_click({'button': 'x2'})

        self.assertEqual(
            events,
            [(25, 3, 10.0, 20.0), (26, 3, 10.0, 20.0),
             (25, 4, 10.0, 20.0), (26, 4, 10.0, 20.0)],
        )

    def test_middle_click_posts_center_button_down_then_up(self):
        events = []
        with patch.object(mouse_service, '_get_pos', return_value=(10.0, 20.0)), patch.object(
            mouse_service, '_post_mouse_event', side_effect=lambda *args: events.append(args)
        ), patch.object(mouse_service.time, 'sleep'):
            mouse_service.handle_click({'button': 'middle'})

        self.assertEqual(events, [(25, 2, 10.0, 20.0), (26, 2, 10.0, 20.0)])

    def test_drag_motion_posts_left_dragged_events_while_left_button_is_held(self):
        events = []
        warps = []
        with patch.object(mouse_service, '_get_pos', return_value=(10.0, 20.0)), patch.object(
            mouse_service, '_post_mouse_event', side_effect=lambda *args: events.append(args)
        ), patch.object(mouse_service, '_warp', side_effect=lambda *args: warps.append(args)):
            mouse_service.mac_down('left')
            events.clear()
            mouse_service.mac_move(5, 7)
            drag_events = list(events)
            mouse_service.mac_up('left')

        self.assertEqual(drag_events, [(6, 0, 15.0, 27.0)])
        self.assertEqual(warps, [])

    def test_move_ignores_null_delta_instead_of_crashing_socketio_handler(self):
        warps = []
        with patch.object(mouse_service, '_get_pos', return_value=(10.0, 20.0)), patch.object(
            mouse_service, '_warp', side_effect=lambda *args: warps.append(args)
        ):
            mouse_service.handle_move({'dx': None, 'dy': 3})

        self.assertEqual(warps, [(10.0, 23.0)])

    def test_disconnect_release_restores_regular_pointer_warp(self):
        events = []
        warps = []
        with patch.object(mouse_service, '_get_pos', return_value=(10.0, 20.0)), patch.object(
            mouse_service, '_post_mouse_event', side_effect=lambda *args: events.append(args)
        ), patch.object(mouse_service, '_warp', side_effect=lambda *args: warps.append(args)):
            mouse_service.mac_down('left')
            mouse_service.release_all_buttons()
            mouse_service.mac_move(3, 4)

        self.assertEqual(events, [(1, 0, 10.0, 20.0), (2, 0, 10.0, 20.0)])
        self.assertEqual(warps, [(13.0, 24.0)])

    def test_scroll_preserves_horizontal_axis_and_mac_direction(self):
        deltas = []
        with patch.object(
            mouse_service, '_post_scroll', side_effect=lambda *args: deltas.append(args)
        ):
            mouse_service.handle_scroll({'dx': 2, 'dy': 3, 'speed': 2})

        self.assertEqual(deltas, [(-30, -20)])

    def test_smooth_scroll_keeps_pixel_scale(self):
        deltas = []
        with patch.object(
            mouse_service, '_post_scroll', side_effect=lambda *args: deltas.append(args)
        ):
            mouse_service.handle_scroll({'dx': 10, 'dy': 20, 'smooth': True})

        self.assertEqual(deltas, [(-20, -10)])

    def test_smooth_pixel_deltas_accumulate_into_wheel_steps(self):
        old_x = mouse_service._SMOOTH_SCROLL_X
        old_y = mouse_service._SMOOTH_SCROLL_Y
        mouse_service._SMOOTH_SCROLL_X = mouse_service._SMOOTH_SCROLL_Y = 0.0
        try:
            self.assertEqual(mouse_service._smooth_pixels_to_wheel_steps(0, 20), (0, 0))
            self.assertEqual(mouse_service._smooth_pixels_to_wheel_steps(0, 20), (0, 1))
            self.assertEqual(mouse_service._smooth_pixels_to_wheel_steps(-40, 0), (-1, 0))
        finally:
            mouse_service._SMOOTH_SCROLL_X = old_x
            mouse_service._SMOOTH_SCROLL_Y = old_y

    def test_created_mouse_event_is_posted_then_released(self):
        posted = []
        released = []
        quartz = SimpleNamespace(
            CGEventCreateMouseEvent=lambda *_args: 17,
            CGEventPost=lambda _tap, event: posted.append(event),
        )
        with patch.object(mouse_service, '_quartz', quartz), patch.object(
            mouse_service, '_release_event', side_effect=released.append
        ):
            mouse_service._post_mouse_event(1, 0, 10.0, 20.0)

        self.assertEqual(posted, [17])
        self.assertEqual(released, [17])


if __name__ == '__main__':
    unittest.main()
