#!/usr/bin/python

import os
import sys
import urllib2

class Update(object):

    # configuration
#    repo = "https://raw.githubusercontent.com/KLUSEK/BMW-RPi-iBUS/master/"
    repo = "http://shared.kluczek.net/"
    files = ["agent.py", "ibus.py", "bluetooth.py", "bluezutils.py", "ibus_test.py", "update.py"]

    def start(self):
        error = False
        pwd = os.path.dirname(os.path.realpath(sys.argv[0]))
        
        for file in self.files:
            try:
                handle = urllib2.urlopen(self.repo + file)
                with open(pwd + "/" + file,'wb') as output:
                    output.write(handle.read())
                    print("Update %s file: OK" % file)
            except urllib2.HTTPError, e:
                error = True
                print("Update %s file: %s" % (file, e))
        
        return not error
    
if __name__ == '__main__':
    u = Update()
    u.start()