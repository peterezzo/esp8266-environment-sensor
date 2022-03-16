"""
Wifi-remote ESP8266 and DHT22 Temperature and Humidity MQTT Logger

Author: Pete Ezzo <peter.ezzo@gmail.com>

In Micropython
"""

import dht  # type: ignore
import json
import machine  # type: ignore
import network  # type: ignore
import ntptime  # type: ignore
import struct
import time
import umqtt.simple as umqtt  # type: ignore
import webrepl  # type: ignore


NETWORK_DELAY = 0.3


class Config():
    def __init__(self) -> None:
        print('Starting config')
        with open('config.json') as f:
            config = json.load(f)
            for k, v in config.items():
                setattr(self, k, v)

    def __getattr__(self, _):
        return None


class MQTT():
    def __init__(self) -> None:
        print('Starting MQTT')
        location = config.location or umqtt.hexlify(machine.unique_id())
        client = umqtt.MQTTClient(location, config.broker_host, config.broker_port, config.broker_user,
                                  config.broker_pass, config.broker_keepalive or 30)
        self.client = client
        self.disconnect = self.client.disconnect

        client.set_callback(self.callback)
        client.connect()
        topics = [(b'Commands/ALL', 1), (b'Commands/%s' % config.location.encode(), 1)]
        for topic in topics:
            client.subscribe(*topic)
        for _ in range(5):
            time.sleep(0.1)
            client.check_msg()

    def publish(self, topic: str, msg: str) -> None:
        self.client.check_msg()
        self.client.publish(topic.encode(), msg.encode())
        time.sleep(0.1)
        self.client.check_msg()

    def callback(self, topic: bytes, msg: bytes) -> None:
        print('Starting callback')
        global stayon
        if msg == b'check-in' or msg == b'check in':
            self.publish('Notifications/check-in-reply', config.location)
        elif msg == b'stay on':
            stayon = True
            self.publish('Notifications/Sensors', 'Sensor %s online at %s' % (config.location, wlan.ifconfig()[0]))


def startwifi() -> None:
    print('Starting wifi')
    network.WLAN(network.AP_IF).active(False)
    if config.wifi_ssid and config.wifi_psk:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            wlan.connect(config.wifi_ssid, config.wifi_psk)
            for _ in range(600):
                if wlan.isconnected():
                    break
                time.sleep(0.1)
            else:
                raise ConnectionError('WiFi cannot connect')
        print('network config:', wlan.ifconfig())
        return wlan


def setclock() -> None:
    print('Starting NTP')
    if config.ntp_enable:
        if config.ntp_host:
            ntptime.host = config.ntp_host
        if rtc.memory() and time.time() - struct.unpack('<I', rtc.memory())[0] < 300:
            return
        ntptime.settime()
        rtc.memory(struct.pack('<I', time.time()))
        print('time set by NTP')


def sendsensordata() -> None:
    """
    Reads a data structure to configure DHT22 sensors on multiple pins
    Example: { "terrarium-cold": 1, "terrarium-center": 2, "terrarium-hot": 3 }
    """
    mqtt = MQTT()
    for name, pin in config.sensors.items():
        print('Measuring sensor', name)
        sensor = dht.DHT22(machine.Pin(pin))

        try:
            sensor.measure()
        except OSError as e:
            print(e)
            mqtt.publish('Notifications/%s/errors' % name, 'Sensor read error')
        else:
            mqtt.publish('Sensors/%s/Temperature_C' % name, str(sensor.temperature()))
            mqtt.publish('Sensors/%s/Humidity_Pct' % name, str(sensor.humidity()))
    time.sleep(NETWORK_DELAY)
    mqtt.disconnect()


def webreplstart() -> None:
    print('Starting webrepl')
    if config.webrepl_enable:
        webrepl.start(password=config.webrepl_password)


def deepsleep(delta: int) -> None:
    print('deep sleeping')
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
    rtc.alarm(rtc.ALARM0, 60000 - delta)
    machine.deepsleep()


# program executes here
start = time.ticks_ms()
stayon = False
try:
    config = Config()
    rtc = machine.RTC()
    wlan = startwifi()
    setclock()
    sendsensordata()
except KeyboardInterrupt:
    stayon = True
except Exception as e:
    print('ERROR', e)
finally:
    delta = time.ticks_diff(time.ticks_ms(), start)
    print('Loop took', delta, 'ms ticks')
    if stayon:
        webreplstart()
    else:
        deepsleep(delta)
