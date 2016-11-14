#!/usr/bin/python

import sys
import time
import threading
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import bluetooth as bt_
import ibus as ibus_

bluetooth = None
ibus = None

def main():
    global bluetooth
    bluetooth = bt_.BluetoothService()
    global ibus
    ibus = ibus_.IBUSService()
    
    ibus.commands = ibus_.IBUSCommands(ibus)
    
    ibus.thread = threading.Thread(target=ibus.start)
    ibus.thread.daemon = True
    ibus.thread.start()

    time.sleep(15)
    bluetooth.reconnect()
    ibus.commands.clown_nose_on()
    ibus.send("3008801a3500414243d7")
    ibus.send(ibus.commands.generate_display_packet("CONNECTED"))
    
    
    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        print("Unable to run the gobject main loop")
        
    bluetooth.shutdown()
    ibus.shutdown()
    ibus.thread = None
    sys.exit(0)


if __name__ == '__main__':
    main()