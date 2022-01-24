"""
Micropython Syslog Wrapper

Author: Pete Ezzo <peter.ezzo@gmail.com>
"""

try:
    import usocket as socket  # type: ignore
except ImportError:
    import socket


class Syslog():
    def __init__(self, host: str, port: int) -> None:
        self.remote = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.loghost = (host, port)

    def warn(self, msg: str) -> None:
        data = "<%d>%s" % (4 + 3*8, msg)  # 4: WARN, 3*8: DAEMON
        self.sendto(data)

    def info(self, msg: str) -> None:
        data = "<%d>%s" % (6 + 3*8, msg)  # 6: INFO, 3*8: DAEMON
        self.sendto(data)

    def sendto(self, data: str) -> None:
        self.remote.sendto(data, self.loghost)
