#!/usr/bin/python

import os
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
import bluezutils

# Based on
# https://github.com/pauloborges/bluez/tree/master

CLIENT_MAC = os.path.dirname(os.path.realpath(sys.argv[0])) + "/client"

class BluetoothService:
    
    player = {"status": None, "artist": None, "title": None}
    MediaPlayer1_object_path = None

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
            print("==================================")
            print("Device %s connected" % bt_addr)
            print("==================================")
            cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 200%%" % bt_addr
            #cmd = "pactl load-module module-loopback source=bluez_source.%s; pactl set-sink-volume 0 175%%; pactl set-port-latency-offset bluez_card.%s phone-output 13000000" % (bt_addr, bt_addr)
            os.system(cmd)

            try:
                with open(CLIENT_MAC, "w") as f:
                    f.write(bt_addr.replace("_", ":"))
            except Exception as error: 
                print("Could not save client address to file")

        else:
            print("=====================================")
            print("Device %s disconnected" % bt_addr)
            print("=====================================")
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
        self.MediaPlayer1_object_path = path

        if iface == "MediaControl1":
            if "Connected" in changed:
                if changed["Connected"]:
                    print("MediaControl is connected [{}] and interface [{}]".format(path, iface))

        if iface == "MediaPlayer1":
            if "Status" in changed:
                    self.player["status"] = changed["Status"]
            if "Track" in changed:
                    self.player["artist"] = changed["Track"]["Artist"] if "Artist" in changed["Track"] else None
                    self.player["title"] = changed["Track"]["Title"] if "Title" in changed["Track"] else None

    #		if changed["Status"] == 'playing':
    #	    		print('tutaj ustawienie latency')

    def player_control(self, action):
        iface = dbus.Interface(bus.get_object(bluezutils.SERVICE_NAME, self.MediaPlayer1_object_path), bluezutils.MEDIACONTROL_INTERFACE)
        if action == "play":
            iface.Play()
        elif action == "pause":
            iface.Pause()
        elif action == "previous":
            iface.Previous()
        elif action == "next":
            iface.Next()
        else:
            return False

    def reconnect(self):
        if os.path.isfile(CLIENT_MAC) and os.path.getsize(CLIENT_MAC) > 0:
            try:
                client_mac = open(CLIENT_MAC).read()
            except Exception as error:
                return False
            
            device = bluezutils.find_device(client_mac)
            return bluezutils.dev_connect(device.object_path)
        else:
            return False

    def shutdown(self):
        self.manager.UnregisterAgent(self.path)
        print("Bluetooth agent unregistered")