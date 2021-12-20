"""
Wifi-remote ESP8266 and DHT22 Temperature and Humidity Logger

Author: Pete Ezzo <peter.ezzo@gmail.com>

In Micropython
"""

import dht
import json
import machine
import network
import time
try:
    import usocket as socket
except:
    import socket


def configure():
    print('Starting config')
    with open('config.json') as f:
        config = json.load(f)
    print('Loaded config')
    return config


def wifi(config):
    print('Starting WiFi')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(config['ssid'], config['psk'])
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())
    print('Started WiFi')
    return wlan


def main(config):
    print('Starting main')
    remote = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    loghost = (config['host'], config['port'])
    location = config['location']
    sensor = dht.DHT22(machine.Pin(config['pin']))

    print('Entering main loop')
    while True:
        try:
            sensor.measure()
            temperature = sensor.temperature()
            humidity = sensor.humidity()

            print('temperature = %.2f' % temperature)
            print('humidity    = %.2f' % humidity)
            print('')

            data = "<%d>%s" % (6 + 3*8, json.dumps({'location': location, 'temperature': temperature, 'humidity': humidity})) # 6: INFO, 3*8: DAEMON
        except OSError as e:
            print('data read error')
            print('')

            data = "<%d>%s" % (4 + 3*8, json.dumps({'error': str(e)}))  # 4: WARN, 3*8: DAEMON

        remote.sendto(data, loghost)

        time.sleep(5)


# program executes here
while True:
    config = configure()
    wlan = wifi(config)
    try:
        main(config)
    except KeyboardInterrupt:
        print('Bailing out')
        break
    except Exception as e:
        print('Broke something:', str(e))
