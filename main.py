import state_machine

def sub_cb(topic, msg): #topic is the topic sep32 is subscribed to
  print((topic, msg))
  if topic == b'lighttime' and msg == b'received':
    print('ESP received hello message')

def connect_and_subscribe():
  global client_id, mqtt_server, topic_sub #global so we can access them throughout the code
  client = MQTTClient(client_id, mqtt_server) #mqtt_server is the IP address of the Rpi-192.168.100.204
  client.set_callback(sub_cb)
  client.connect() #connects client to the broker
  client.subscribe(topic_sub)
  print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt_server, topic_sub))
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  machine.reset()

try:
  client = connect_and_subscribe()
except OSError as e:
  restart_and_reconnect()

while True:
  try:
    #new_message = client.check_msg()
    fsm = StateMachine()
    client.check_msg()
    if (time.time() - last_message) > message_interval: #to check whether 5secs have passed since the last message was sent
      msg = b'Hello #%d' % counter
      client.publish(topic_pub, msg)
      last_message = time.time()
      counter += 1
  except OSError as e:
    restart_and_reconnect()


