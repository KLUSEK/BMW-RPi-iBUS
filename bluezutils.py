#!/usr/bin/python

import dbus

SERVICE_NAME = "org.bluez"
ADAPTER_INTERFACE = SERVICE_NAME + ".Adapter1"
DEVICE_INTERFACE = SERVICE_NAME + ".Device1"
AGENT_INTERFACE = SERVICE_NAME + ".Agent1"
MEDIACONTROL_INTERFACE = SERVICE_NAME + ".MediaControl1"
MEDIAPLAYER_INTERFACE = SERVICE_NAME + ".MediaPlayer1"

BT_DEVICE_NAME = "BMW Multimedia"
BT_PIN_CODE = "50233"

def show_adapter_info():
    bus = dbus.SystemBus()
    om = dbus.Interface(bus.get_object(SERVICE_NAME, "/"), "org.freedesktop.DBus.ObjectManager")
    objects = om.GetManagedObjects()
    for path, interfaces in objects.iteritems():
        if ADAPTER_INTERFACE not in interfaces:
            continue

        print(" [ %s ]" % (path))
        props = interfaces[ADAPTER_INTERFACE]

        for (key, value) in props.items():
            if (key == "Class"):
                print("    %s = 0x%06x" % (key, value))
            elif (key == "UUIDs"):
                continue                
            else:
                print("    %s = %s" % (key, value))
        print()

def get_adapter_address():
    objects = get_managed_objects()
    bus = dbus.SystemBus()
    for path, ifaces in objects.iteritems():
        adapter = ifaces.get(ADAPTER_INTERFACE)
        if adapter is None:
            continue
        return adapter["Address"]
    return False
        
def get_managed_objects():
	bus = dbus.SystemBus()
	manager = dbus.Interface(bus.get_object(SERVICE_NAME, "/"),
				"org.freedesktop.DBus.ObjectManager")
	return manager.GetManagedObjects()

def find_adapter(pattern=None):
	return find_adapter_in_objects(get_managed_objects(), pattern)

def find_adapter_in_objects(objects, pattern=None):
	bus = dbus.SystemBus()
	for path, ifaces in objects.iteritems():
		adapter = ifaces.get(ADAPTER_INTERFACE)
		if adapter is None:
			continue
		if not pattern or pattern == adapter["Address"] or \
							path.endswith(pattern):
			obj = bus.get_object(SERVICE_NAME, path)
			return dbus.Interface(obj, ADAPTER_INTERFACE)
	raise Exception("Bluetooth adapter not found")

def find_device(device_address, adapter_pattern=None):
	return find_device_in_objects(get_managed_objects(), device_address,
								adapter_pattern)

def find_device_in_objects(objects, device_address, adapter_pattern=None):
	bus = dbus.SystemBus()
	path_prefix = ""
	if adapter_pattern:
		adapter = find_adapter_in_objects(objects, adapter_pattern)
		path_prefix = adapter.object_path
	for path, ifaces in objects.iteritems():
		device = ifaces.get(DEVICE_INTERFACE)
		if device is None:
			continue
		if (device["Address"] == device_address and
						path.startswith(path_prefix)):
			obj = bus.get_object(SERVICE_NAME, path)
			return dbus.Interface(obj, DEVICE_INTERFACE)

	raise Exception("Bluetooth device not found")

def set_trusted(path):
	bus = dbus.SystemBus()
	props = dbus.Interface(bus.get_object(SERVICE_NAME, path), "org.freedesktop.DBus.Properties")
	props.Set(DEVICE_INTERFACE, "Trusted", True)

def dev_connect(path):
    try:
        bus = dbus.SystemBus()
        dev = dbus.Interface(bus.get_object(SERVICE_NAME, path), DEVICE_INTERFACE)
        dev.Connect()
        return True
    except Exception as ex:
        print("Unable to connect device. '{0}'".format(ex.message))
        return False

def dev_disconnect(path):
    try:
        bus = dbus.SystemBus()
        dev = dbus.Interface(bus.get_object(SERVICE_NAME, path), DEVICE_INTERFACE)
        dev.Disconnect()
        return True
    except Exception as ex:
        print("Unable to disconnect device. '{0}'".format(ex.message))
        return False
    
class Agent(dbus.service.Object):
	@dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
	def AuthorizeService(self, device, uuid):
		print("AuthorizeService (%s, %s)" % (device, uuid))
		set_trusted(device)
		print("Trust device (%s)" % device)
		return

	@dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
	def RequestPinCode(self, device):
		print("RequestPinCode (%s)" % (device))
		set_trusted(device)
		print("Trust device (%s)" % device)
		return BT_PIN_CODE

	@dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
	def RequestAuthorization(self, device):
		print("RequestAuthorization (%s)" % (device))
		return

	@dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
	def Cancel(self):
		print("Cancel")
