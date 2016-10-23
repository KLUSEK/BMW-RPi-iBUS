#!/usr/bin/python

import os
import sys
import signal
import logging
import logging.handlers
import dbus
import dbus.service
import dbus.mainloop.glib
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import bluezutils

LOG_LEVEL = logging.INFO
#LOG_LEVEL = logging.DEBUG
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

CONNECTION_NAME = "BMW Multimedia System"
BUS_NAME = 'org.bluez'
MEDIAPLAYER_PATH = None

BT_CLIENT_LOG_FILE = "bt_addr.log"

def show_adapter_info():
	om = dbus.Interface(bus.get_object(BUS_NAME, "/"), "org.freedesktop.DBus.ObjectManager")
	objects = om.GetManagedObjects()
	for path, interfaces in objects.iteritems():
		if "org.bluez.Adapter1" not in interfaces:
			continue

		print(" [ %s ]" % (path))
		props = interfaces["org.bluez.Adapter1"]

		for (key, value) in props.items():
			if (key == "Class"):
				print("    %s = 0x%06x" % (key, value))
			else:
				print("    %s = %s" % (key, value))
		print()

def set_trusted(path):
	props = dbus.Interface(bus.get_object(BUS_NAME, path), "org.freedesktop.DBus.Properties")
	props.Set("org.bluez.Device1", "Trusted", True)

def dev_connect(path):
	dev = dbus.Interface(bus.get_object(BUS_NAME, path), "org.bluez.Device1")
	dev.Connect()

class Rejected(dbus.DBusException):
	_dbus_error_name = "org.bluez.Error.Rejected"

class Agent(dbus.service.Object):
	exit_on_release = True

	def set_exit_on_release(self, exit_on_release):
		self.exit_on_release = exit_on_release

	@dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
	def Release(self):
		print("Release")
		if self.exit_on_release:
			mainloop.quit()

	@dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
	def AuthorizeService(self, device, uuid):
#		logger.info("AuthorizeService (%s, %s)" % (device, uuid))
		print("AuthorizeService (%s, %s)" % (device, uuid))
		set_trusted(device)
		print("Trust device (%s)" % device)
		return

	@dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
	def Cancel(self):
		print("Cancel")

#def pair_reply():
#	logger.info("Device paired: %s") % dev_path
#	print("Device paired: %s") % dev_path
#	set_trusted(dev_path)
#	dev_connect(dev_path)
#	mainloop.quit()

def pair_error(error):
	err_name = error.get_dbus_name()
	if err_name == "org.freedesktop.DBus.Error.NoReply" and device_obj:
		print("Timed out. Cancelling pairing")
		device_obj.CancelPairing()
	else:
		print("Creating device failed: %s" % (error))

	mainloop.quit()

def device_property_changed(property_name, value, path, interface, device_path):
	if property_name != "org.bluez.MediaControl1":
		return

	device = dbus.Interface(bus.get_object(BUS_NAME, device_path), "org.freedesktop.DBus.Properties")
	properties = device.GetAll("org.bluez.MediaControl1")

#	logger.info("Getting dbus interface for device: %s interface: %s property_name: %s" % (device_path, interface, property_name))
	print("Getting dbus interface for device: %s interface: %s property_name: %s" % (device_path, interface, property_name))

       	bt_addr = "_".join(device_path.split('/')[-1].split('_')[1:])

	if properties["Connected"]:
		print("Device: %s connected" % bt_addr)
	        cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 175%%" % bt_addr
#	        cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 175%%; pactl set-port-latency-offset bluez_card.%s phone-output 13000000" % (bt_addr, bt_addr)
#	        logger.info("Running cmd: %s" % cmd)
	        os.system(cmd)
		
		try:
			with open(os.path.dirname(os.path.realpath(sys.argv[0])) + '/' + BT_CLIENT_LOG_FILE, "w") as f:
				f.write(bt_addr)
		except Exception as error: 
			print("Could not save bt_addr to file")

	else:
	        print("Device: %s disconnected" % bt_addr)
	        cmd = "for i in $(pactl list short modules | grep module-loopback | grep source=bluez_source.%s | cut -f 1); do pactl unload-module $i; done" % bt_addr
#	       	logger.info("Running cmd: %s" % cmd)
	        os.system(cmd)

def interfaces_removed(path, interfaces):
	for iface in interfaces:
		if not(iface in ["org.bluez.Adapter1", "org.bluez.Device1"]):
			continue
#		logger.info("{Removed %s} [%s] ... Exiting." % (iface, path))
		print("Adapter removed: %s [%s] ... Terminate!" % (iface, path))
		mainloop.quit()

def player_changed(interface, changed, invalidated, path):
#        logger.info("Interface [{}] changed [{}] on path [{}]".format(interface, changed, path))
        iface = interface[interface.rfind(".") + 1:]
	MEDIAPLAYER_PATH = path

        if iface == "MediaControl1":
            if "Connected" in changed:
                if changed["Connected"]:
                    print("MediaControl is connected [{}] and interface [{}]".format(path, iface))

        if iface == "MediaPlayer1":
            if "Track" in changed:
		print("Artist: {}".format(changed["Track"]["Artist"]))
                print("Title: {}".format(changed["Track"]["Title"]))
            if "Status" in changed:
                print("Status changed to: {}".format(changed["Status"]))

#		if changed["Status"] == 'playing':
#	    		print('tutaj ustawienie latency')
#			mp = dbus.Interface(bus.get_object(BUS_NAME, path), "org.bluez.MediaPlayer1")
#			mp.Next()


def shutdown(signum, frame):
	mainloop.quit()

if __name__ == '__main__':
	# shut down on a TERM signal
	signal.signal(signal.SIGTERM, shutdown)

	# start logging
#	logger = logging.getLogger("bluez_python_agent")
#	logger.setLevel(LOG_LEVEL)
#	logger.addHandler(logging.handlers.SysLogHandler(address = "/dev/log"))
#	logger.info("Starting to log Bluetooth communication")

	# Get the system bus
	try:
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
		bus = dbus.SystemBus()
	except Exception as ex:
#		logger.error("Unable to get the system dbus: '{0}'. Exiting. Is dbus running?".format(ex.message))
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

	show_adapter_info()

	path = "/test/agent"
	agent = Agent(bus, path)

	obj = bus.get_object(BUS_NAME, "/org/bluez");
	manager = dbus.Interface(obj, "org.bluez.AgentManager1")
	manager.RegisterAgent(path, "NoInputNoOutput")

#	logger.info("Agent Manager registered")
	print("AgentManager registered")

	# listen for signal of remove adapter
	bus.add_signal_receiver(interfaces_removed, bus_name=BUS_NAME, dbus_interface="org.freedesktop.DBus.ObjectManager", signal_name="InterfacesRemoved")

	# listen for signals on the Bluez bus
	bus.add_signal_receiver(device_property_changed, bus_name=BUS_NAME, signal_name="PropertiesChanged", path_keyword="device_path", interface_keyword="interface")

	# listen for signal of changing properties
        bus.add_signal_receiver(player_changed, bus_name=BUS_NAME, dbus_interface="org.freedesktop.DBus.Properties", signal_name="PropertiesChanged", path_keyword="path")

 #       logger.info("Signals receiver registered")
        print("Signals receiver registered")

	manager.RequestDefaultAgent(path)

	try:
        	mainloop = GObject.MainLoop()
		mainloop.run()
	except KeyboardInterrupt:
		pass
	except:
#		logger.error("Unable to run the gobject main loop")
		print("Unable to run the gobject main loop")
		sys.exit(1)

	sys.exit(0)


	#adapter.UnregisterAgent(path)
	#print("Agent unregistered")
