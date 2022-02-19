"""
Wifi-remote ESP8266 and DHT22 Temperature and Humidity Logger

Author: Pete Ezzo <peter.ezzo@gmail.com>

In Micropython
"""

import dht  # type: ignore
import json
import machine  # type: ignore
import network  # type: ignore
import ntptime  # type: ignore
import time
import umqtt.simple  # type: ignore
import webrepl  # type: ignore


class Config():
    def __init__(self) -> None:
        print('Starting config')
        with open('config.json') as f:
            config = json.load(f)

        self.config = config
        self.wlan = None

        self.webrepl()
        self.wifi()
        self.ntp()

        print('Loaded config')

    def webrepl(self) -> None:
        if self.config.get('webrepl_enable') and self.config.get('webrepl_password'):
            webrepl.start(password=self.config['webrepl_password'])

    def wifi(self) -> None:
        network.WLAN(network.AP_IF).active(False)
        if self.config.get('wifi_ssid') and self.config.get('wifi_psk'):
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            if not wlan.isconnected():
                print('connecting to network...')
                wlan.connect(self.config['wifi_ssid'], self.config['wifi_psk'])
                while not wlan.isconnected():
                    pass
            print('network config:', wlan.ifconfig())
            print('Started WiFi')

    def ntp(self) -> None:
        if self.config.get('ntp_enable'):
            print('attempting to set NTP')
            if self.config.get('ntp_host'):
                ntptime.host = self.config['ntp_host']
            ntptime.settime()
            print('time set by NTP')

    def __getitem__(self, key):
        return self.config[key]


class MQTT():
    def __init__(self, server, port=1883, user=None, password=None, keepalive=60, connect=True):
        client_id = umqtt.simple.hexlify(machine.unique_id())
        self.client = umqtt.simple.MQTTClient(client_id, server, port, user, password, keepalive)

        self.fake_thread = None
        self._subscribed = set()
        self._keepalive = keepalive
        self._reconnect_delay = keepalive // 2

        if connect:
            self._connect()

    def start(self, keepalive_buffer=10):
        self.fake_thread = self._check_msg_loop(keepalive_buffer)

    def check_subs(self):
        if self.fake_thread:
            next(self.fake_thread)
        else:
            raise ValueError('Call .start before this method')

    def pub(self, topic, msg, retain=False, qos=0):
        """
        Publish a message to a topic on the broker
        qos of 0 will not check, will appear to work even if broker connection is down
        qos of 1 will check broker connection is up and message was sent
        """
        try:
            self.client.publish(topic, msg, retain, qos)
            print('Published to', topic)
        except OSError as e:
            print('Error', e)
            self._connect()

    def sub(self, callback, topic, qos=0):
        """
        Subscribe to a topic and set the callback function
        This must be called after a connect if the connection has dropped
        """
        self.client.set_callback(callback)
        self.client.subscribe(topic, qos)
        print('Subscribed to', topic)

    def _check_msg_loop(self, keepalive_buffer=10):
        """
        This is a yield-based coroutine to maintain connection during other operations
        """
        last_checkin = 0
        checkin_interval = self._keepalive - keepalive_buffer
        while True:
            now = time.time()
            if now - last_checkin > checkin_interval:
                print('Pinging broker')
                self.client.ping()
                last_checkin = now
            try:
                self.client.check_msg()
            except OSError as e:
                print('Error', e)
                self._connect()
            yield

    def _handle_msg_cb(self, topic, msg):
        if topic == b'Commands/ALL' and msg == b'check-in':
            self.pub(b'Notifications/check-in-reply', config['location'].encode(), qos=1)

    def _connect(self):
        while True:
            try:
                print('Connecting to server')
                self.client.connect()
                break
            except OSError as e:
                print('Connect error', e)
                time.sleep(self._reconnect_delay)
        self.sub(self._handle_msg_cb, 'Commands/ALL')


class Logger(MQTT):
    """Formatting class that extends MQTT wrapper"""
    def send_sensor_data(self, data: dict) -> None:
        print('Sending data', data)
        for pack in data:
            topic = 'Sensors/' + pack['sensor']
            payload = json.dumps({'temperature': '%.2f' % pack['temperature'], 'humidity': '%.2f' % pack['humidity']})
            self.pub(topic, payload)

    def error(self, *args) -> None:
        topic = getattr(self, 'base_topic', 'Logs/Misc') + '/Errors'
        print('ERROR', *args)
        self.pub(topic, ' '.join(args))

    def log(self, *args):
        topic = getattr(self, 'base_topic', 'Logs/Misc') + '/Logs'
        print(*args)
        self.pub(topic, ' '.join(args))


class Sensors():
    def __init__(self, sensorconfig: dict) -> None:
        """
        Reads a data structure to configure DHT22 sensors on multiple pins
        Example: { "terrarium-cold": 1, "terrarium-center": 2, "terrarium-hot": 3 }
        """
        self.sensors = {}
        for sensor, pin in sensorconfig.items():
            self.sensors[sensor] = dht.DHT22(machine.Pin(pin))

    def read(self) -> list:
        results = []
        for name, sensor in self.sensors.items():
            try:
                sensor.measure()
            except OSError:
                logger.error('Sensor', name, 'read error')
                continue
            temperature = sensor.temperature()
            humidity = sensor.humidity()

            results.append({'sensor': name, 'temperature': temperature, 'humidity': humidity})
        return results


class Controller:
    """This actually controls everything"""
    def __init__(self) -> None:
        logger.base_topic = 'Logs/' + config['location']
        logger.log('Starting up at', )

    def start(self):
        print('Entering main loop')
        logger.start()
        while True:
            try:
                start = time.ticks_ms()
                self.main()
                print('Loop took', time.ticks_diff(time.ticks_ms(), start), 'ms ticks')
                time.sleep(5)
            except KeyboardInterrupt:
                print('Breaking')
                break
            except Exception as e:
                print('ERROR-MAIN-LOOP', str(e))
                time.sleep(15)

    def main(self) -> None:
        logger.check_subs()
        sensorvalues = sensors.read()
        logger.send_sensor_data(sensorvalues)


# program executes here
config = Config()
logger = Logger(config['broker_host'], config['broker_port'], config['broker_user'], config['broker_password'])
sensors = Sensors(config['sensors'])
controller = Controller()

controller.start()
