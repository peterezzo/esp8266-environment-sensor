"""
Wifi-remote ESP8266 and DHT22 Temperature and Humidity Logger

Author: Pete Ezzo <peter.ezzo@gmail.com>

In Micropython
"""

import dht
import json
import machine
import time

import wifi
import syslog


def configure():
    print('Starting config')
    with open('config.json') as f:
        config = json.load(f)
    print('Loaded config')
    return config


def main(config):
    print('Starting main')
    location = config['location']
    sensor = dht.DHT22(machine.Pin(config['pin']))
    logger = syslog.Syslog(config['host'], config['port'])

    print('Entering main loop')
    while True:
        try:
            sensor.measure()
            temperature = sensor.temperature()
            humidity = sensor.humidity()

            print('temperature = %.2f' % temperature)
            print('humidity    = %.2f' % humidity)
            print('')
            logger.info(json.dumps({'location': location, 'temperature': temperature, 'humidity': humidity}))

        except OSError as e:
            print('data read error')
            print('')
            logger.warn(json.dumps({'error': str(e)}))

        time.sleep(5)


# program executes here
while True:
    config = configure()
    wifi.client(config['ssid'], config['psk'])
    try:
        main(config)
    except KeyboardInterrupt:
        print('Bailing out')
        break
    except Exception as e:
        print('Broke something:', str(e))
