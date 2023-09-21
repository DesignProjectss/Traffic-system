import time
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
esp.osdebug(None)
import gc
gc.collect() #garbage collection

ssid = 'Village people'
password = 'catch fire'
mqtt_server = '192.168.100.204'
client_id = ubinascii.hexlify(machine.unique_id())
topic_sub = b'lighttime'# topic esp32 is subscribed to
topic_pub = b'hello Rpi, how are you doing'# topic it is published to

last_message = 0 #holds the last time a message was sent
message_interval = 5 #time between each message sent
counter = 0 #counter to be added to the message

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(ssid, password)

while station.isconnected() == False:
  pass

print('Connection successful')
print(station.ifconfig())
