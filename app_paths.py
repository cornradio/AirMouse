import os
import sys


def is_frozen():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def resource_dir():
    """Read-only bundled resources (templates / static / certs)."""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def app_dir():
    """Writable directory next to the exe, or the project root in source mode."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    return os.path.join(resource_dir(), *parts)


def app_path(*parts):
    return os.path.join(app_dir(), *parts)
