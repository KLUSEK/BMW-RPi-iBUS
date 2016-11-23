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

def onIBUSpacket():
    pass

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
#    if event_data["state"] is None or \
#        event_data["artist"] is None or \
#        event_data["title"] is None:
#        return

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

    player["state"] = event_data["state"]
    player["artist"] = event_data["artist"]
    player["title"] = event_data["title"]

def main():
    global bluetooth
    global ibus
        
    bluetooth = bt_.BluetoothService(onPlayerChanged)
    ibus = ibus_.IBUSService(onIBUSready)
    ibus.commands = ibus_.IBUSCommands(ibus)
    
    ibus.thread = threading.Thread(target=ibus.start)
    ibus.thread.daemon = True
    ibus.thread.start()

    #bluetooth.reconnect()

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