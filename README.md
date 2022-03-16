# Wifi-remote ESP8266 and DHT22 Temperature and Humidity Logger

These use a NodeMCU ESP8266 dev board, a DHT22 sensor, and a 10k pullup resistor.  
Logs are sent by TCP MQTT to local collector, no qos or retries.
The system deep sleeps after sending each measurement, waking once per minute.

## NodeMCU Setup

Hold flash button and hit reset on NodeMCU

    esptool --port /dev/ttyUSB0 --baud 115200 erase_flash
    esptool --port /dev/ttyUSB0 --baud 115200 write_flash --flash_size=detect -fm dout 0 ~/esp8266/esp8266-20210902-v1.17.bin

Hit reset button on NodeMCU

    ampy --port /dev/ttyUSB0 ls
    ampy --port /dev/ttyUSB0 put main.py
    ampy --port /dev/ttyUSB0 put environment.py
    ampy --port /dev/ttyUSB0 put outside-config.json config.json
    ampy --port /dev/ttyUSB0 ls

Hit reset button on NodeMCU

    screen /dev/ttyUSB0 115200

## Doing more with the data

See https://github.com/peterezzo/iotcloud
