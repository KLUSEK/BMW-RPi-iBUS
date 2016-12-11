#!/usr/bin/python

# Simple script to easy testing IBUS commands

import sys
import time
import threading
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import ibus as ibus_

ibus = None

def fake_callback(p=None):
    pass

def onIBUSpacket(packet):
    if packet.source_id == "60" and packet.destination_id == "3f":
        print packet.raw

def main():
    global ibus
    ibus = ibus_.IBUSService(fake_callback, onIBUSpacket)
    ibus.commands =  ibus_.IBUSCommands(ibus)
    
    ibus.thread = threading.Thread(target=ibus.start)
    ibus.thread.daemon = True
    ibus.thread.start()

    print("Waiting 5 sec...")
    time.sleep(5)
    ibus.send("3f03601b47")
    print("Command sent.")
    print("Finished.")

    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        print("Unable to run the gobject main loop")

    if ibus.main_thread.isAlive():
        print "Stopping IBUS main thread..."
        ibus.stop()
    ibus.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()