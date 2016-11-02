#!/usr/bin/python

import sys
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject
import unicodedata
import bluetooth as bt

bluetooth = None

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')
    

def main():
    global bluetooth
    bluetooth = bt.Bluetooth()

    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        print("Unable to run the gobject main loop")
        
    bluetooth.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()