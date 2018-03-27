#!/usr/bin/python

import os
import sys
import re
import dbus
import dbus.service
import dbus.mainloop.glib
import bluezutils
import unicodedata

# Based on
# https://github.com/pauloborges/bluez/tree/master

LAST_DEVICE = os.path.dirname(os.path.realpath(sys.argv[0])) + "/.device"

def strip_accents(s):
    try:
        return str("".join(c for c in unicodedata.normalize("NFD", s)
                  if unicodedata.category(c) != "Mn"))
    except:
        return "- - -"

class BluetoothService(object):
    bus = None
    player = {"state": None, "artist": None, "title": None}

    def __init__(self, onBluetoothConnected_callback, onPlayerChanged_callback):
        self.onBluetoothConnected_callback = onBluetoothConnected_callback
        self.onPlayerChanged_callback = onPlayerChanged_callback
        
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
#        self.bus.add_signal_receiver(self.interfaces_removed, bus_name=bluezutils.SERVICE_NAME, dbus_interface="org.freedesktop.DBus.ObjectManager", signal_name="InterfacesRemoved")

        # listen for signals on the Bluez bus
        self.bus.add_signal_receiver(self.device_property_changed, bus_name=bluezutils.SERVICE_NAME, signal_name="PropertiesChanged", path_keyword="device_path", interface_keyword="interface")

        # listen for signal of changing properties
        self.bus.add_signal_receiver(self.player_changed, bus_name=bluezutils.SERVICE_NAME, dbus_interface="org.freedesktop.DBus.Properties", signal_name="PropertiesChanged", path_keyword="path")

        print("Signals receiver registered")

        self.manager.RequestDefaultAgent(self.path)

    def device_property_changed(self, property_name, value, path, interface, device_path):
        if property_name != "org.bluez.MediaControl1":
            return

        device = dbus.Interface(self.bus.get_object(bluezutils.SERVICE_NAME, device_path), "org.freedesktop.DBus.Properties")
        properties = device.GetAll("org.bluez.MediaControl1")

        print("Getting dbus interface for device: %s interface: %s property_name: %s" % (device_path, interface, property_name))

        bt_addr = "_".join(device_path.split('/')[-1].split('_')[1:]).replace("_", ":")

        if properties["Connected"]:
            print("==================================")
            print("Device %s connected" % bt_addr)
            print("==================================")

            os.system("pactl set-sink-volume 0 153%%")
            self.onBluetoothConnected_callback(True, bt_addr)

            try:
                with open(LAST_DEVICE, "w") as f:
                    f.write(bt_addr)
            except Exception as error: 
                print("Could not save client address to file")
        else:
            print("=====================================")
            print("Device %s disconnected" % bt_addr)
            print("=====================================")
            
            self.onBluetoothConnected_callback(False)

    def interfaces_removed(self, path, interfaces):
        for iface in interfaces:
            if not(iface in [bluezutils.ADAPTER_INTERFACE, "org.bluez.Device1"]):
                continue
            print("Adapter removed: %s [%s] ... Terminate!" % (iface, path))
            self.shutdown()

    def player_changed(self, interface, changed, invalidated, path):
        iface = interface[interface.rfind(".") + 1:]

        if re.match( r'.*\/player\d+', path):
            self._player_object_path = path

#        if iface == "MediaControl1":
#            if "Connected" in changed:
#                if changed["Connected"]:
#                    print("MediaControl is connected [{}] and interface [{}]".format(path, iface))

        if iface == "MediaPlayer1":
            if "Status" in changed:
                self.player["state"] = strip_accents(changed["Status"])

                # call the callback
                self.onPlayerChanged_callback(self.player)
            
            if "Track" in changed:
                self.player["artist"] = strip_accents(changed["Track"]["Artist"]) if "Artist" in changed["Track"] else None
                self.player["title"] = strip_accents(changed["Track"]["Title"]) if "Title" in changed["Track"] else None
                    
                # call the callback
                self.onPlayerChanged_callback(self.player)

    def player_control(self, action):
        iface = dbus.Interface(self.bus.get_object(bluezutils.SERVICE_NAME, self._player_object_path), bluezutils.MEDIAPLAYER_INTERFACE)
        
        try:
            if action == "play":
                iface.Play()
            elif action == "pause":
                iface.Pause()
            elif action == "stop":
                iface.Stop()
            elif action == "prev":
                iface.Previous()
            elif action == "next":
                iface.Next()
            elif action == "forward":
                iface.FastForward()
            elif action == "rewind":
                iface.Rewind()
            else:
                return False
        except Exception as ex:
            print("Player communicate error: '{0}'".format(ex.message))
            return False

    def reconnect(self):
        if os.path.isfile(LAST_DEVICE) and os.path.getsize(LAST_DEVICE) > 0:
            try:
                last_device = open(LAST_DEVICE).read()
            except Exception as error:
                return False
            
            device = bluezutils.find_device(last_device)
            return bluezutils.dev_connect(device.object_path)
        else:
            return False
        
    def disconnect(self, adapter):
        device = bluezutils.find_device(adapter)
        return bluezutils.dev_disconnect(device.object_path)

    def shutdown(self):
        self.manager.UnregisterAgent(self.path)
        print("Bluetooth agent unregistered")