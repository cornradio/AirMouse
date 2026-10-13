"""Environment-controlled console diagnostics."""

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from debug_logging import debug_log, debug_socket_event


class DebugLoggingTests(unittest.TestCase):
    def test_debug_log_is_silent_unless_debug_is_enabled(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'DEBUG': '0'}), redirect_stdout(output):
            debug_log('mouse', 'move', dx=1, dy=2)
        self.assertEqual(output.getvalue(), '')

    def test_debug_log_prints_event_details_when_enabled(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'DEBUG': '1'}), redirect_stdout(output):
            debug_log('mouse', 'move', dx=1, dy=2)
        self.assertIn('[DEBUG] mouse.move', output.getvalue())
        self.assertIn("'dx': 1", output.getvalue())

    def test_text_event_logs_length_without_logging_typed_contents(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'DEBUG': '1'}), redirect_stdout(output):
            debug_socket_event('type_text', {'text': 'private text'})
        self.assertIn("'characters': 12", output.getvalue())
        self.assertNotIn('private text', output.getvalue())


if __name__ == '__main__':
    unittest.main()
