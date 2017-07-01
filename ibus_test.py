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

def onIBUSready():
    pass

def onIBUSpacket(packet):
    
    print(packet)

def main():
    global ibus

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
    
    print("")
    shutdown()
    sys.exit(0)

def shutdown():
    global ibus

    if ibus.main_thread.isAlive():
        print("Stopping IBUS main thread...")
        ibus.stop()

    print("Destroying IBUS service...")
    ibus.shutdown()
    
if __name__ == '__main__':
    main()