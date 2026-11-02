"""CI-only pytest plugin: fail closed on outbound network, including DNS."""
import socket


def pytest_configure(config):
    def blocked(*args, **kwargs):
        raise AssertionError("CI offline: network access is forbidden during tests")
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked
