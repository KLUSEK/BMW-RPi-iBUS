#!/usr/bin/python

import sys
import time
#import threading
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import ibus as ibus_

ibus = None

def main():
    global ibus
    ibus = ibus_.IBUSService()

    time.sleep(5)
    #12 znakow
    print("WYSYLAM !!!!!!!!!!!!!!!!!!!!!!")
    print("WYSYLAM !!!!!!!!!!!!!!!!!!!!!!")
    print("WYSYLAM !!!!!!!!!!!!!!!!!!!!!!")
        
    ibus.write_to_ibus('c81180234232c720425420524541445920c878')
    #11 znakow
    #ibus.write_to_ibus('c81080234232c7425420524541445920c858')
    #ibus.write_to_ibus('c80a8023423248656c6c6f53')
        

    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        print("Unable to run the gobject main loop")
        
    ibus.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()