import paho.mqtt.client as mqtt
import argparse
import time




def parse_updates(msg):
    lines = msg.splitlines()

    updates = [line.split(' ') for line in lines]
    for u in updates:
        if len(u) == 5:
            try:
                u = [int(c) for c in u]
                print("setting ({},{}) to RGB({},{},{})".format(*u))
                strip.setPixelColor(*u) 
            except:
                print("Error.")
        elif len(u) == 3:
            try:
                u = [int(c) for c in u]
                print("setting floor to RGB({},{},{})".format(*u))
                for p in range(122):
                    strip.setPixelColor(p, Color(*u))
            except:
                print("Error.")           
        else:
            print("(Invalid Command)" + str(u))
    strip.show()


def on_connect(client, userdata, flags, rc):
     print("Connected With Result Code {}".format(rc))
     client.subscribe("ledfloorupdates")


def on_disconnect(client, userdata, rc):
	print("Disconnected From Broker")


def on_message(client, userdata, message):
    msg = message.payload.decode()
    parse_updates(msg)


# Set up MQTT client
broker_address = "10.90.154.80"
broker_port = 1883
client = mqtt.Client()

#Assigning the object attribute to the Callback Function
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

client.connect(broker_address, broker_port)
client.loop_forever() # Note: is non-blocking

print ('Press Ctrl-C to quit.')


