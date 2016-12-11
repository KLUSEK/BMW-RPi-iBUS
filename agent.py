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
import rfcomm as rfcomm_

bluetooth = None
ibus = None

DATA = {
    "bluetooth": {
        "adapter": None,
        "connected": False,
#        "last_device": None
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
        "ignition": False,
        "speed": None,
        "rpm": None,
        "outside": None,
        "coolant": None,
        "mileage": None,
        "lights": False
    },
    "pdc": {
        "active": False
    }
}

def hex2int(v, nbits=7):
    v = int(v, 16)
    return v if v < (1 << nbits) else v - (1 << nbits + 1)

def onIBUSready():
    ibus.cmd.clown_nose_on()
    ibus.cmd.request_for_mileage()
    ibus.cmd.request_for_ignition()
    
def onBluetoothConnected(state, adapter=None):
    global ibus
    global DATA

    DATA["bluetooth"]["connected"] = state

    if state: # connected
        DATA["bluetooth"]["adapter"] = adapter
    else: # disconnected | reset adapter MAC address and stop RADIO display thread
        DATA["bluetooth"]["adapter"] = None
        try:
            while ibus.display_thread.isAlive():
                ibus.cmd.print_stop()
            ibus.cmd.print_clear()
        except:
            pass

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
                packet = ibus.cmd.get_display_packet("BT ERROR", "connect")
                ibus.send(packet.raw)
            else:
                print("      -> BT Connected")
                packet = ibus.cmd.get_display_packet("CONNECTED", "connect")
                ibus.send(packet.raw)
            return

    if packet.raw == "5003c8019a":
        print("### Pressed: R/T button")

        ibus.cmd.clown_nose_on()
        ibus.cmd.request_for_pdc()
        ibus.cmd.request_for_sensors()
        
        ibus.send("3b0580410401fa")

        # Nothing binded yet

    # split hex string into list of values
    data = []
    data = [packet.data[i:i+2] for i in range(0, len(packet.data), 2)]

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
            
            print("Ignition state: %s" % data[1])
        """
        R_Gear detection
        80 0A BF 13 02 10 00 00 00 00 38 CK // in reverse
        80 0A BF 13 02 00 00 00 00 00 38 CK  // out of reverse
        """
        if data[0] == "13":
            print "WSTECZNY!!!!!!!!!!! " + packet.data
#            if data[2] == "10":
#                print "WSTECZNY: ON!###########"
#            elif data[2] == "00":
#                print "WSTECZNY: OFF!##########"
        # Mileage
        elif data[0] == "17":
            DATA["obc"]["mileage"] = (int(data[7], 16) * 65536) + (int(data[6], 16) * 256) + int(data[5], 16)
            
            print("Mileage: %d" % DATA["obc"]["mileage"])
        # Speed/RPM
        elif data[0] == "18":
            DATA["obc"]["speed"] = int(data[1], 16) * 2
            DATA["obc"]["rpm"] = int(data[2], 16) * 100
            
            print("Speed: %d km/h, RPM: %d" % (int(data[1], 16)*2, int(data[2], 16)*100))
        # Temperatures
        elif data[0] == "19":
            DATA["obc"]["outside"] = hex2int(data[1])
            DATA["obc"]["coolant"] = hex2int(data[2])

            print("Outside: %d (C), Coolant: %d (C)" % (hex2int(data[1]), hex2int(data[2])))

        return

    """
    * Handle OBC messages sent from IKE
    * IBus Message: 80 0C FF 24 <System> 00 <Data> <CRC>
    
    Base on: https://github.com/t3ddftw/DroidIBus/blob/master/app/src/main/java/com/ibus/droidibus/ibus/systems/BroadcastSystem.java
    """
    if packet.source_id == "80" and packet.destination_id == "ff":
#        # Fuel 1
#        elif data[1] == "04":
#            str = ''.join([data[2], data[3], data[4], data[5], data[6]])
#            str = str.decode("hex")
#            print("Fuel 1: %s" % str)
#        # Fuel 2    
#        elif data[1] == "05":
#            str = ''.join([data[2], data[3], data[4], data[5], data[6]])
#            str = str.decode("hex")
#            print("Fuel 2: %s" % str)
#        # range
#        elif data[1] == "06":
#            str = ''.join([data[2], data[3], data[4], data[5], data[6]])
#            str = str.decode("hex")
#            print("Range: %s" % str)
#        # Distanse
#        elif data[1] == "07":
#            str = ''.join([data[2], data[3], data[4], data[5], data[6]])
#            str = str.decode("hex")
#            print("distanse: %s" % str)
#        # AVG speed
#        elif data[1] == "0a":
#            str = ''.join([data[2], data[3], data[4], data[5], data[6]])
#            str = str.decode("hex")
#            print("avg speed: %s" % str) 
#        else:
        print("NIEZNANE dane")
        print(packet.raw)
 
    """
    PDC Park Distance Control
    """
#    if packet.source_id == "60":
#        print("###### PDC active!")
#        ibus.send("3f03601b47")
#        print packet.raw
        
    if packet.source_id == "60" and packet.destination_id == "3f":
        print "PDC: " + packet.raw

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

    try:
        if ibus.main_thread.isAlive():
            print "Stopping IBUS main thread..."
            ibus.stop()
    except:
        print "tutaj sie wyjebalo1"

    try:
        print "Destroying IBUS service..."
        ibus.shutdown()
    except:
        print "tutaj sie wyjebalo2"
    bluetooth.shutdown()

if __name__ == '__main__':
    main()