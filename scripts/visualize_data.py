import matplotlib
matplotlib.use('TkAgg')  # Specify a backend that supports threading

import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt
import json
from matplotlib.animation import FuncAnimation

SLOT_DURATION = 0.01 # seconds

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("opentestbed/uinject/arrived")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())  # Parse JSON data
    update_plot(data)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

broker_address = "argus.paris.inria.fr"
broker_port = 1883

client.connect(broker_address, broker_port, 60)
client.loop_start()

# Initialize an empty plot with appropriate labels
plt.figure()
plt.xlabel("Number of Samples")
plt.ylabel("Average Latency (second)")
plt.title("Live Data Plot")
plt.grid()

# Initialize empty lists to store data
time_data = []
data_to_plot = {}

def update_plot(data):

    if type(data) == type(data_to_plot):

        if data['src_id'] in data_to_plot.keys():
            data_to_plot[data['src_id']].append(data['avg_latency']*SLOT_DURATION)
        else:
            data_to_plot[data['src_id']] = [data['avg_latency']*SLOT_DURATION]

        for src_id in data_to_plot.keys():

            # Update the plot with new data
            plt.plot(data_to_plot[src_id], '-^',color='b')

# Use the FuncAnimation to update the plot in a separate thread
ani = FuncAnimation(plt.gcf(), update_plot, interval=1000)

# Keep the plot open until manually closed
plt.show()
