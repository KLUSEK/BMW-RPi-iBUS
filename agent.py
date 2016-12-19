#!/usr/bin/python

import os
import sys
import threading
try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject
import bluetooth as bt_
import ibus as ibus_
#import rfcomm as rfcomm_

bluetooth = None
ibus = None

DATA = {
    "bluetooth": {
        "adapter": None,
        "connected": False,
    },
    "rfcomm": {
        "connected": False 
    },
    "player": {
        "state": None,
        "artist": None,
        "title": None
    },
    "obc": {
        "vin": None,
        "ignition": None,
        "speed": None,
        "rpm": None,
        "outside": None,
        "coolant": None,
        "mileage": None,
        "fuel_1": None,
        "fuel_2": None,
        "range": None,
        "avg_speed": None,
        "lights": False
    },
    "pdc": {
        "active": False,
        "sensor_1": None,
        "sensor_2": None,
        "sensor_3": None,
        "sensor_4": None
    }
}

def hex2int(v, nbits=7):
    v = int(v, 16)
    return v if v < (1 << nbits) else v - (1 << nbits + 1)

def onIBUSready():
    ibus.cmd.clown_nose_on()
    
    ibus.cmd.reset_fuel_2()

    ibus.cmd.request_for_ignition()
    ibus.cmd.request_for_mileage()
    ibus.cmd.request_for_fuel_1()
    ibus.cmd.request_for_range()
    ibus.cmd.request_for_distance()
    ibus.cmd.request_for_avg_speed()
    ibus.cmd.request_for_limit()
    ibus.cmd.request_for_sensors()

def onBluetoothConnected(state, adapter=None):
    global ibus
    global DATA

    DATA["bluetooth"]["connected"] = state

    try:
        while ibus.display_thread.isAlive():
            ibus.cmd.print_stop()
        ibus.cmd.print_clear()
    except:
        pass

    if state: # connected
        DATA["bluetooth"]["adapter"] = adapter
        packet = ibus.cmd.get_display_packet("CONNECTED", "connect")
    else: # disconnected | reset adapter MAC address and stop RADIO display thread
        DATA["bluetooth"]["adapter"] = None
        packet = ibus.cmd.get_display_packet("BT OFF", "connect")
    
    ibus.send(packet.raw)

def onIBUSpacket(packet):
    global DATA

    """
    MFL Multi Functional Steering Wheel Buttons:
    50 04 68 32 10 1E - Volume Down button pressed
    50 04 68 32 11 1F - Volume Up button pressed
    50 04 68 3B 08 0F - Previous button pressed once
    50 04 68 3B 18 1F - Previous button (long press)
    50 04 68 3B 21 26 - Next button pressed once
    50 04 68 3B 11 16 - Next button (long press)
    50 04 C8 3B 80 27 - DIAL button
    50 04 C8 3B 90 37 - DIAL button (long press)
    50 03 C8 01 9A    - R/T button
    """
    if packet.raw == "5004683b080f":
        print("### Pressed: Previous button")
        if DATA["bluetooth"]["connected"]:
            print("      -> Previous song")
            bluetooth.player_control("prev")
            return

    if packet.raw == "5004683b181f":
        print("### Pressed (long): Previous button")
        if DATA["bluetooth"]["connected"]:
            print("      -> Rewind")
            bluetooth.player_control("rewind")
            return

    if packet.raw == "5004683b2126":
        print("### Pressed: Next button")
        if DATA["bluetooth"]["connected"]:
            print("      -> Next song")
            bluetooth.player_control("next")
            return
            
    if packet.raw == "5004683b1116":
        print("### Pressed (long): Next button")
        if DATA["bluetooth"]["connected"]:
            print("      -> Fast Forward")
            bluetooth.player_control("forward")
            return

    if packet.raw == "5004c83b8027":
        print("### Pressed: DIAL button")
        if DATA["bluetooth"]["connected"]:
            if DATA["player"]["state"] == "playing":
                print("      -> Pause song")
                bluetooth.player_control("pause")
            else:
                print("      -> Play song")
                bluetooth.player_control("play")
            return
                
    if packet.raw == "5004c83b9037":
        print("### Pressed (long): DIAL button")
        if not DATA["bluetooth"]["connected"]:
            print("      -> BT Connecting")
            packet = ibus.cmd.get_display_packet("CONNECTING", "connect")
            ibus.send(packet.raw)
            if not bluetooth.reconnect():
                print("      -> BT Error")
                packet = ibus.cmd.get_display_packet("ERROR", "connect")
                ibus.send(packet.raw)
            return

    if packet.raw == "5003c8019a":
        print("### Pressed: R/T button")

        ibus.cmd.clown_nose_on()
        ibus.cmd.request_for_vin()
        ibus.cmd.request_for_distance()
        ibus.cmd.request_for_limit()
        ibus.cmd.request_for_fuel_1()
        ibus.cmd.request_for_fuel_2()
        # Nothing binded yet

    # split hex string into list of values
    data = []
    data = [packet.data[i:i+2] for i in range(0, len(packet.data), 2)]
    
    # looking for vehicle VIN
    if packet.source_id == "d0" and packet.destination_id == "80":
        print("VIN:")
        print(data[1].decode("hex") + data[2].decode("hex") + data[3] + data[4] + data[5])
        
        return

    """
    OBC (On Board Computer)
    Messages from the IKE to the GlobalBroadcast
    0x11 - Ignition state
    0x13 - Reversing, Handbrake, Oil presure state
    0x15 - OBC units
    0x17 - Mileage
    0x18 - Speed/RPM
    0x19 - Temp

    Base on: https://github.com/t3ddftw/DroidIBus/blob/master/app/src/main/java/com/ibus/droidibus/ibus/systems/GlobalBroadcastSystem.java
    """
    if packet.source_id == "80" and packet.destination_id == "bf":
        # Ignition status
        if data[0] == "11":
            DATA["obc"]["ignition"] = int(data[1], 16)

            # print("Ignition state: %d" % DATA["obc"]["ignition"])
        """
        R_Gear detection
        80 0A BF 13 02 10 00 00 00 00 38 CK // in reverse
        80 0A BF 13 02 00 00 00 00 00 38 CK  // out of reverse
        """
        if data[0] == "13":
            if (int(data[2], 16) >> 4) == 1:
                # decrease volume while reversing
                if not DATA["pdc"]["active"]:
                    ibus.cmd.volume_down()
                DATA["pdc"]["active"] = True
            else:
                # increase volume after reversing
                if DATA["pdc"]["active"]:
                    ibus.cmd.volume_up()
                DATA["pdc"]["active"] = False
        # Mileage
        elif data[0] == "17":
            DATA["obc"]["mileage"] = (int(data[3], 16)*65536) + (int(data[2], 16)*256) + int(data[1], 16)
            
            # print("Mileage: %d (km)" % DATA["obc"]["mileage"])
        # Speed/RPM
        elif data[0] == "18":
            DATA["obc"]["speed"] = int(data[1], 16) * 2
            DATA["obc"]["rpm"] = int(data[2], 16) * 100

            # print("Speed: %d km/h, RPM: %d" % (DATA["obc"]["speed"], DATA["obc"]["rpm"]))
        # Temperatures
        elif data[0] == "19":
            DATA["obc"]["outside"] = hex2int(data[1])
            DATA["obc"]["coolant"] = hex2int(data[2])

            print("Outside: %d (C), Coolant: %d (C)" % (DATA["obc"]["outside"], DATA["obc"]["coolant"]))
            
        elif data[0] == "5b":
            print("Light Status:")
            print(packet.raw)

        return

    """
    * Handle OBC messages sent from IKE
    * IBus Message: 80 0C FF 24 <System> 00 <Data> <CRC>
    
    Base on: https://github.com/t3ddftw/DroidIBus/blob/master/app/src/main/java/com/ibus/droidibus/ibus/systems/BroadcastSystem.java
    https://github.com/t3ddftw/DroidIBus/blob/master/app/src/main/java/com/ibus/droidibus/ibus/systems/GFXNavigationSystem.java
    """    
    if packet.source_id == "80" and packet.destination_id == "ff":
        # Fuel 1
        if data[1] == "04":
            try:
                DATA["obc"]["fuel_1"] = float(packet.data[4:14].lstrip("00").decode("hex"))
            except:
                DATA["obc"]["fuel_1"] = None
            print("Fuel 1: %f" % DATA["obc"]["fuel_1"])
        # Fuel 2    
        elif data[1] == "05":
            try:
                DATA["obc"]["fuel_2"] = float(packet.data[4:14].lstrip("00").decode("hex"))
            except:
                DATA["obc"]["fuel_2"] = None
            print("Fuel 2: %f" % DATA["obc"]["fuel_2"])
        # Range
        elif data[1] == "06":
            try:
                DATA["obc"]["range"] = float(packet.data[4:14].lstrip("00").decode("hex"))
            except:
                DATA["obc"]["range"] = None
            print("Range: %f" % DATA["obc"]["range"])
        # Distance
        elif data[1] == "07":
            print("Distance: %s" % packet.raw)
        # Speed limit
        elif data[1] == "09":
            print("Limit: %s" % packet.raw)
        # AVG speed
        elif data[1] == "0a":
            try:
                DATA["obc"]["avg_speed"] = float(packet.data[4:14].lstrip("00").decode("hex"))
            except:
                DATA["obc"]["avg_speed"] = None
            print("AVG speed: %f" % DATA["obc"]["avg_speed"])
            
        return
 
    """
    PDC Park Distance Control
    """
    # Gong status - use it for sending DIAG request for distance
    if packet.source_id == "60" and packet.destination_id == "80" and DATA["pdc"]["active"]:
        ibus.cmd.request_for_pdc()

    # DIAG responce from PDC cointaing information about distance for each sensor
    if packet.source_id == "60" and packet.destination_id == "3f":
        DATA["pdc"]["sensor_1"] = int(data[2], 16)
        DATA["pdc"]["sensor_2"] = int(data[3], 16)
        DATA["pdc"]["sensor_3"] = int(data[4], 16)
        DATA["pdc"]["sensor_4"] = int(data[5], 16)

        print("Sensor #1: %d" % DATA["pdc"]["sensor_1"])
        print("Sensor #2: %d" % DATA["pdc"]["sensor_2"])
        print("Sensor #3: %d" % DATA["pdc"]["sensor_3"])
        print("Sensor #4: %d" % DATA["pdc"]["sensor_4"])
        print ""

def onPlayerChanged(event_data):
    global DATA

    """
    Wait untill all data is set
    to avoid sending crap to CDP display
    """
    if ibus.handle is None or \
        event_data["state"] is None or \
        event_data["artist"] is None or \
        event_data["title"] is None:
        return
    
    print("[%s] %s - %s" % (event_data["state"], event_data["artist"], event_data["title"]))

    """
    Send first packet with proper icon in the begining if only state changed
    """    
    if DATA["player"]["artist"] == event_data["artist"] and \
        DATA["player"]["title"] == event_data["title"] and \
        not DATA["player"]["state"] == event_data["state"]:

        packet = ibus.cmd.get_display_packet(event_data["artist"], event_data["state"])
        ibus.send(packet.raw)

    """
    Finish ongoing display thread
    """
    try:
        while ibus.display_thread.isAlive():
            ibus.cmd.print_stop()
        ibus.cmd.print_clear()
    except:
        pass

    """
    Do animation in separated thread ...
    """
    if event_data["state"] == "playing":
        ibus.display_thread = threading.Thread(target=ibus.cmd.print_on_display, \
                                   kwargs={"data": [event_data["artist"], event_data["title"]]})
        ibus.display_thread.daemon = True
        ibus.display_thread.start()

    DATA["player"].update(event_data)

def main():
    global bluetooth
    global ibus

    bluetooth = bt_.BluetoothService(onBluetoothConnected, onPlayerChanged)

    ibus = ibus_.IBUSService(onIBUSready, onIBUSpacket)
    ibus.cmd = ibus_.IBUSCommands(ibus)
    
    ibus.main_thread = threading.Thread(target=ibus.start)
    ibus.main_thread.daemon = True
    ibus.main_thread.start()

    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        print("Unable to run the gobject main loop")
    
    print ''
    shutdown()
    sys.exit(0)
    
def shutdown():
    global bluetooth
    global ibus
    
    try:
        print "Stopping RADIO display thread..."
        while ibus.display_thread.isAlive():
            ibus.cmd.print_stop()
        ibus.cmd.print_clear()
    except:
        pass

    if ibus.main_thread.isAlive():
        print "Stopping IBUS main thread..."
        ibus.stop()

    print "Destroying IBUS service..."
    ibus.shutdown()
    bluetooth.shutdown()

if __name__ == '__main__':
    main()