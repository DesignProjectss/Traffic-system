from machine import Pin

pu= Pin(12,Pin.OUT)
print('say something..')
command=input()
if command=='Hello ESP32':
    pu.on()
    print('what is thy bidding my master')

