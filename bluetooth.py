#!/usr/bin/python

import os
import sys
import unicodedata
import dbus
import dbus.service
import dbus.mainloop.glib
import bluezutils

# Based on
# https://github.com/pauloborges/bluez/tree/master/test

CLIENT_ADDR_FILE = "client"

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

def write_to_file(file, str):
    full_file_path = os.path.dirname(os.path.realpath(sys.argv[0])) + "/" + file
    try:
        with open(full_file_path, "w") as f:
            f.write(str)
            return True
        except Exception as error: 
            print("Could not save client address to file")
            return False

def read_from_fle(file):
    full_file_path = os.path.dirname(os.path.realpath(sys.argv[0])) + "/" + file
    if os.path.isfile(full_file_path) and os.path.getsize(full_file_path) > 0:
        return open(full_file_path).read()
    else:
        return False


class BluetoothService:
    def __init__(self):
        # Get the system bus
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self.bus = dbus.SystemBus()
        except Exception as ex:
            print("Unable to get the system dbus: '{0}'. Exiting. Is dbus running?".format(ex.message))
            return False

        adapter_path = bluezutils.find_adapter(None).object_path
        adapter = dbus.Interface(self.bus.get_object(bluezutils.SERVICE_NAME, adapter_path), "org.freedesktop.DBus.Properties")

        # Power on adapter
        adapter.Set(bluezutils.ADAPTER_INTERFACE, "Powered", dbus.Boolean(1))
        # Set name to display in available connections
        adapter.Set(bluezutils.ADAPTER_INTERFACE, "Alias", bluezutils.BT_DEVICE_NAME)
        # Set pairable on
        adapter.Set(bluezutils.ADAPTER_INTERFACE, "Pairable", dbus.Boolean(1))
        # Set discoverable on
        adapter.Set(bluezutils.ADAPTER_INTERFACE, "Discoverable", dbus.Boolean(1))
        # Set discoverable timeout to 0
        adapter.Set(bluezutils.ADAPTER_INTERFACE, "DiscoverableTimeout", dbus.UInt32(0))
        # Set paraible time out to 0
        adapter.Set(bluezutils.ADAPTER_INTERFACE, "PairableTimeout", dbus.UInt32(0))

        bluezutils.show_adapter_info()

        self.path = "/test/agent"
        agent = bluezutils.Agent(self.bus, self.path)

        obj = self.bus.get_object(bluezutils.SERVICE_NAME, "/org/bluez");
        self.manager = dbus.Interface(obj, "org.bluez.AgentManager1")
        self.manager.RegisterAgent(self.path, "NoInputNoOutput")

        print("Bluetooth AgentManager registered")

        # listen for signal of remove adapter
        self.bus.add_signal_receiver(self.interfaces_removed, bus_name=bluezutils.SERVICE_NAME, dbus_interface="org.freedesktop.DBus.ObjectManager", signal_name="InterfacesRemoved")

        # listen for signals on the Bluez bus
        self.bus.add_signal_receiver(self.device_property_changed, bus_name=bluezutils.SERVICE_NAME, signal_name="PropertiesChanged", path_keyword="device_path", interface_keyword="interface")

        # listen for signal of changing properties
        self.bus.add_signal_receiver(self.player_changed, bus_name=bluezutils.SERVICE_NAME, dbus_interface="org.freedesktop.DBus.Properties", signal_name="PropertiesChanged", path_keyword="path")

        print("Signals receiver registered")

        self.manager.RequestDefaultAgent(self.path)

        # remove all old loopback ever created
        os.system("for i in $(pactl list short modules | grep module-loopback | grep source=bluez_source. | cut -f 1); do pactl unload-module $i; done")
        
    def device_property_changed(self, property_name, value, path, interface, device_path):
        if property_name != "org.bluez.MediaControl1":
            return

        device = dbus.Interface(self.bus.get_object(bluezutils.SERVICE_NAME, device_path), "org.freedesktop.DBus.Properties")
        properties = device.GetAll("org.bluez.MediaControl1")

        print("Getting dbus interface for device: %s interface: %s property_name: %s" % (device_path, interface, property_name))

        bt_addr = "_".join(device_path.split('/')[-1].split('_')[1:])

        if properties["Connected"]:
            print("Device %s connected" % bt_addr)
            cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 200%%" % bt_addr
            #cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 175%%; pactl set-port-latency-offset bluez_card.%s phone-output 13000000" % (bt_addr, bt_addr)
            os.system(cmd)

            write_to_file(CLIENT_ADDR_FILE, bt_addr)


        else:
            print("Device %s disconnected" % bt_addr)
            cmd = "for i in $(pactl list short modules | grep module-loopback | grep source=bluez_source.%s | cut -f 1); do pactl unload-module $i; done" % bt_addr
            os.system(cmd)

    def interfaces_removed(self, path, interfaces):
        for iface in interfaces:
            if not(iface in [bluezutils.ADAPTER_INTERFACE, "org.bluez.Device1"]):
                continue
            print("Adapter removed: %s [%s] ... Terminate!" % (iface, path))
            self.shutdown()

    def player_changed(self, interface, changed, invalidated, path):
        iface = interface[interface.rfind(".") + 1:]
    #    MEDIAPLAYER_PATH = path

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

    def shutdown(self):
        self.manager.UnregisterAgent(self.path)
        print("Bluetooth agent unregistered")