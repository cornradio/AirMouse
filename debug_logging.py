"""Small opt-in console diagnostics shared by Socket.IO and input adapters."""

import os


def debug_log(component, event, **details):
    """Print a structured event line only when ``DEBUG=1`` is set."""
    if os.environ.get('DEBUG') != '1':
        return
    print(f'[DEBUG] {component}.{event} {details!r}', flush=True)


def debug_socket_event(event, data=None, sid=None):
    """Log an incoming Socket.IO event without exposing typed text contents."""
    if event == 'type_text':
        text = data.get('text', '') if isinstance(data, dict) else ''
        details = {'characters': len(text) if isinstance(text, str) else 0}
    else:
        details = {'data': data}
    if sid:
        details['sid'] = sid
    debug_log('socket', event, **details)
