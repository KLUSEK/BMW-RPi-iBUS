#!/usr/bin/python

import os
import sys
import signal
import unicodedata
import dbus
import dbus.service
import dbus.mainloop.glib
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import bluezutils

# https://github.com/pauloborges/bluez/tree/master/test

CONNECTION_NAME = 'BMW Multimedia System'
BUS_NAME = 'org.bluez'
MEDIAPLAYER_PATH = None

LAST_BT_CLIENT_FILE = 'client'

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

def device_property_changed(property_name, value, path, interface, device_path):
	if property_name != "org.bluez.MediaControl1":
		return

	device = dbus.Interface(bus.get_object(BUS_NAME, device_path), "org.freedesktop.DBus.Properties")
	properties = device.GetAll("org.bluez.MediaControl1")

	print("Getting dbus interface for device: %s interface: %s property_name: %s" % (device_path, interface, property_name))

       	bt_addr = "_".join(device_path.split('/')[-1].split('_')[1:])

	if properties["Connected"]:
		print("Device %s connected" % bt_addr)
	        cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 175%%" % bt_addr
#	        cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 175%%; pactl set-port-latency-offset bluez_card.%s phone-output 13000000" % (bt_addr, bt_addr)
	        os.system(cmd)

		try:
			with open(os.path.dirname(os.path.realpath(sys.argv[0])) + "/" + LAST_BT_CLIENT_FILE, "w") as f:
				f.write(bt_addr)
		except Exception as error: 
			print("Could not save client address to file")

	else:
	        print("Device %s disconnected" % bt_addr)
	        cmd = "for i in $(pactl list short modules | grep module-loopback | grep source=bluez_source.%s | cut -f 1); do pactl unload-module $i; done" % bt_addr
	        os.system(cmd)

def interfaces_removed(path, interfaces):
	for iface in interfaces:
		if not(iface in ["org.bluez.Adapter1", "org.bluez.Device1"]):
			continue
		print("Adapter removed: %s [%s] ... Terminate!" % (iface, path))
		mainloop.quit()

def player_changed(interface, changed, invalidated, path):
        iface = interface[interface.rfind(".") + 1:]
	MEDIAPLAYER_PATH = path

        if iface == "MediaControl1":
            if "Connected" in changed:
                if changed["Connected"]:
                    print("MediaControl is connected [{}] and interface [{}]".format(path, iface))

        if iface == "MediaPlayer1":
            if "Track" in changed:
		if "Artist" in changed["Track"]:
			print("Artist: " + strip_accents(changed["Track"]["Artist"]))
            if "Track" in changed:
		if "Title" in changed["Track"]:
	                print("Title: " + strip_accents(changed["Track"]["Title"]))
            if "Status" in changed:
                print("Status changed to: " + strip_accents(changed["Status"]))

#		if changed["Status"] == 'playing':
#	    		print('tutaj ustawienie latency')
#			mp = dbus.Interface(bus.get_object(BUS_NAME, path), "org.bluez.MediaPlayer1")
#			mp.Next()


def shutdown(signum, frame):
	mainloop.quit()

if __name__ == '__main__':
	# shut down on a TERM signal
	signal.signal(signal.SIGTERM, shutdown)

	# Get the system bus
	try:
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
		bus = dbus.SystemBus()
	except Exception as ex:
		print("Unable to get the system dbus: '{0}'. Exiting. Is dbus running?".format(ex.message))
		sys.exit(1)

	adapter_path = bluezutils.find_adapter(None).object_path
	adapter = dbus.Interface(bus.get_object(BUS_NAME, adapter_path), "org.freedesktop.DBus.Properties")

	# Power on adapter
	adapter.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
	# Set name to display in available connections
	adapter.Set("org.bluez.Adapter1", "Alias", CONNECTION_NAME)
	# Set pairable on
	adapter.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(1))
	# Set discoverable on
	adapter.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(1))
	# Set discoverable timeout to 0
	adapter.Set("org.bluez.Adapter1", "DiscoverableTimeout", dbus.UInt32(0))
	# Set paraible time out to 0
	adapter.Set("org.bluez.Adapter1", "PairableTimeout", dbus.UInt32(0))

	bluezutils.show_adapter_info()

	path = "/test/agent"
	agent = bluezutils.Agent(bus, path)

	obj = bus.get_object(BUS_NAME, "/org/bluez");
	manager = dbus.Interface(obj, "org.bluez.AgentManager1")
	manager.RegisterAgent(path, "NoInputNoOutput")

	print("AgentManager registered")

	# listen for signal of remove adapter
	bus.add_signal_receiver(interfaces_removed, bus_name=BUS_NAME, dbus_interface="org.freedesktop.DBus.ObjectManager", signal_name="InterfacesRemoved")

	# listen for signals on the Bluez bus
	bus.add_signal_receiver(device_property_changed, bus_name=BUS_NAME, signal_name="PropertiesChanged", path_keyword="device_path", interface_keyword="interface")

	# listen for signal of changing properties
        bus.add_signal_receiver(player_changed, bus_name=BUS_NAME, dbus_interface="org.freedesktop.DBus.Properties", signal_name="PropertiesChanged", path_keyword="path")

        print("Signals receiver registered")

	manager.RequestDefaultAgent(path)

	# remove all old loopback ever created
	os.system("for i in $(pactl list short modules | grep module-loopback | grep source=bluez_source. | cut -f 1); do pactl unload-module $i; done")

	try:
        	mainloop = GObject.MainLoop()
		mainloop.run()
	except KeyboardInterrupt:
		pass
	except:
		print("Unable to run the gobject main loop")

	manager.UnregisterAgent(path)
	print("Agent unregistered")
	sys.exit(0)
