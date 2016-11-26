#!/usr/bin/python

import sys
import threading
try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject
import bluetooth as bt_
import ibus as ibus_

bluetooth = None
ibus = None

connected = False
player = {"state": None, "artist": None, "title": None}

def onIBUSready():
    ibus.commands.clown_nose_on()
    
def onBluetoothConnected(value):
    global connected
    connected = value

def onIBUSpacket(packet):
    """
    MFL Multi Functional Steering Wheel Buttons:
    50 04 68 3B 08 0F - Previous button pressed once
    50 04 68 3B 21 26 - Next button pressed once
    50 04 C8 3B 80 27 - DIAL button
    50 03 C8 01 9A    - R/T button
    """
    if packet.raw == "5004683b080f":
        print("### Pressed: Previous button")
        if connected:
            print("###  -> Previous song")
            bluetooth.player_control("prev")

    if packet.raw == "5004683b2126":
        print("### Pressed: Next button")
        if connected:
            print("      -> Next song")
            bluetooth.player_control("next")

    if packet.raw == "5004c83b8027":
        print("### Pressed: DIAL button")
        if connected:
            if player["state"] == "playing":
                print("      -> Pause song")
                bluetooth.player_control("pause")
            elif player["state"] == "pause":
                print("      -> Play song")
                bluetooth.player_control("play")

    if packet.raw == "5003c8019a":
        print("### Pressed: R/T button")
        if not connected:
            print("      -> BT Connecting")
            packet = ibus.commands.get_display_packet("CONNECTING", "connecting")
            ibus.send(packet.raw)
            if not bluetooth.reconnect():
                print("      -> BT Error")
                packet = ibus.commands.get_display_packet("BT ERROR", "connecting")
                ibus.send(packet.raw)
            else:
                print("      -> BT Connected")
                packet = ibus.commands.get_display_packet("CONNECTED", "connecting")
                ibus.send(packet.raw)

def onPlayerChanged(event_data):
    global ibus
    global player

    """
    Wait untill all data is set
    to avoid sending crap to CDP display
    """
    if ibus.handle is None or \
        event_data["state"] is None or \
        event_data["artist"] is None or \
        event_data["title"] is None:
        return
    
    print("[%s] %s: %s" % (event_data["state"], event_data["artist"], event_data["title"]))

    """
    Send first packet with proper icon in the begining if only state changed
    """    
    if player["artist"] == event_data["artist"] and \
        player["title"] == event_data["title"] and \
        not player["state"] == event_data["state"]:

        packet = ibus.commands.get_display_packet(event_data["artist"], event_data["state"])
        ibus.send(packet.raw)

    """
    Finish ongoing display thread
    """
    try:
        while ibus.thread_display.isAlive():
           ibus.commands._display_stop = True
    except:
        pass

    """
    Do animation in separated thread ...
    """
    ibus.commands._display_stop = False
    ibus.thread_display = threading.Thread(target=ibus.commands.print_on_display, \
                               kwargs={"data": [event_data["artist"], event_data["title"]]})
    ibus.thread_display.daemon = True
    ibus.thread_display.start()

    player.update(event_data)

def main():
    global bluetooth
    global ibus

    bluetooth = bt_.BluetoothService(onBluetoothConnected, onPlayerChanged)
    ibus = ibus_.IBUSService(onIBUSready, onIBUSpacket)
    ibus.commands = ibus_.IBUSCommands(ibus)
    
    ibus.thread = threading.Thread(target=ibus.start)
    ibus.thread.daemon = True
    ibus.thread.start()

    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        print("Unable to run the gobject main loop")
    
    print("\n")
    bluetooth.shutdown()
    ibus.shutdown()
    ibus.thread = None
    ibus.thread_display = None
    ibus.commands._display_stop = True
    sys.exit(0)


if __name__ == '__main__':
    main()