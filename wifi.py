"""
Micropython WiFi Functions Wrapper

Author: Pete Ezzo <peter.ezzo@gmail.com>
"""

import network  # type: ignore


def client(ssid: str, psk: str) -> network.WLAN:
    print('Starting WiFi Client')
    network.WLAN(network.AP_IF).active(False)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(ssid, psk)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())
    print('Started WiFi')
    return wlan
