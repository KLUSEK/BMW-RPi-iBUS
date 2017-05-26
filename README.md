# BMW-RPi-iBUS
Multimedia computer for older BMW cars based on Raspberry Pi

[![IMAGE ALT TEXT HERE](http://img.youtube.com/vi/W3VJtcYz3fo/0.jpg)](http://www.youtube.com/watch?v=W3VJtcYz3fo)

## Python dependenties
python-gobject
python-serial
python-dbus

## Operating System
As this project uses [Raspberry Zero](https://www.raspberrypi.org/products/pi-zero/) I'm gonna utilize Raspbian Jessy Lite distro based on Debian Jessie. 

Recent image file and instruction how to write it on SD Card you can always find on [Raspberry.org download section](https://www.raspberrypi.org/downloads/raspbian/).

Next steps are:
* Perform basic steps to configure new system like changing user's default password, expand partition to whole SDcard space.
* I've got mobile hotspot working in my car, so I configured Wi-Fi connection.
My system works as OpenVPN client of my Home Network. It allows me to easily connect to car via ssh _(optional step)_
* As Raspberry Zero has enought amont of RAM memory for our purposes I decided to [disable SWAP service](https://www.element14.com/community/thread/21377/l/how-do-i-permanently-disable-the-swap-service?displayFullThread=true) in the system to minimalize SD Card degradation _(see another useful topic [Prevent SD-Card Corruption](https://www.raspberrypi.org/forums/viewtopic.php?f=28&t=36533) and [Create a robust Raspberry Pi Setup for 24/7 operation](https://narcisocerezo.wordpress.com/2014/06/25/create-a-robust-raspberry-pi-setup-for-24x7-operation/))_

To make our system even lighter uninstall some more spare packages:

    sudo apt-get remove --purge bluez* omxplayer avahi-daemon libx11-.* x11-common midori lxde python3 python3-minimal libraspberrypi-doc xserver.* x11.* xarchiver xauth xkb-data xinit lightdm lxde.* python-tk python3-tk scratch gtk.* libgtk.* openbox libxt.* lxpanel gnome.* libqt.* libxcb.* libxfont.* lxmenu.* gvfs.* xdg-.* desktop.* tcl.* shared-mime-info penguinspuzzle gsfonts ed mcedit vim-tiny vim-common;sudo rm -rf /usr/share/doc/* /opt/vc/src/hello_pi/hello_video/test.h264;sudo apt-get autoremove;sudo apt-get autoclean


## Audio
### Disable Raspberry Pi's built-in sound chip
> Sometimes it is useful to disable the Raspberry Pi's built-in Broadcom sound chip before installing a new USB sound card so as to make it easier to troubleshooting the new USB sound card. _([Instructables.com](http://www.instructables.com/id/Disable-the-Built-in-Sound-Card-of-Raspberry-Pi/?ALLSTEPS))_

Even if Raspberry Zero doesn't have analog 2.5" jack output Broadcom sound chip is visible by the system.
To simplify future operations on USB DAC adapter I disabled built-in chip.

First step is install ALSA tools:

    sudo apt-get install alsa-utils

Now we need to blacklist right module in [/etc/modprobe.d/alsa-blacklist.conf](BMW-RPi-iBUS/etc/modprobe.d/alsa-blacklist.conf)

_(Related article on [Instructables.com](http://www.instructables.com/id/Disable-the-Built-in-Sound-Card-of-Raspberry-Pi/?ALLSTEPS))_

### Set USB DAC as default

> Now, simply use this command to list your alsa-detected sound cards, and take note of the card number of your preferred device.

>    aplay -l

> Then create/edit the alsa configuration file at ~/.asoundrc, or the system wide one at [/etc/asound.conf](BMW-RPi-iBUS/etc/asound.conf), and paste these lines:

>     pcm.!default {
> 	    type hw
> 	    card 1
> 	    device 0
>     }

>     ctl.!default {
> 	    type hw
> 	    card 1
> 	    device 0
>     }

> changing card 0 to the card number of your sound device.
> Use alsamixer to double check that the default has been set correctly.

_(Related article on [raspberrypi.stackexchange.com](http://raspberrypi.stackexchange.com/a/44825))_

### Setup Pulse Audio
> PulseAudio serves as a proxy to sound applications using existing kernel sound components like ALSA

It will be helpful in project to to "pipe" sound from bluetooth to USB DAC's analog output.

First we need install all packages:

    sudo apt-get install bluez bluez-tools pulseaudio pulseaudio-module-bluetooth

Now we need to make some adjustments in PA's config files.

* Make sure that following options are enabled in file [/etc/pulse/default.pa](BMW-RPi-iBUS/etc/pulse/default.pa)

        ### Automatically load driver modules for Bluetooth hardware
        .ifexists module-bluetooth-policy.so
        load-module module-bluetooth-policy
        .endif

        .ifexists module-bluetooth-discover.so
        load-module module-bluetooth-discover
        .endif

* Adjust options related to audio quality (for example resampling).

    Here we need experiment a little bit. Because PA is pretty CPU consuming we need to find correct configuration for our setup.

    In my case the best results gives me following options in file [/etc/pulse/daemon.conf](BMW-RPi-iBUS/etc/pulse/daemon.conf):

        resample-method = src-sinc-medium-quality
        enable-remixing = no
        enable-lfe-remixing = no
        default-sample-format = s16le
        default-sample-rate = 44100
        alternate-sample-rate = 48000
        default-sample-channels = 2

    CPU usage is stable and below 75% while decoding source sampled in 44100 and quality is rather good.

    If you want to get know more about resampling and other parameters I would recomend these URLs:
    * [Pulse Audio on Raspberry Pi](http://www.crazy-audio.com/2014/09/pulseaudio-on-the-raspbery-pi/)
    * [Pulse Audio Configuration](https://wiki.archlinux.org/index.php/PulseAudio/Configuration)

## Bluetooth

We have installed already packages called bluez & bluez-tools.
So it's time to try communicate our system with other BT device.

https://wiki.archlinux.org/index.php/bluetooth#Bluetoothctl


### Some photos :-)

![alt text](http://i.imgur.com/pkuh65Rl.jpg)
![alt text](http://i.imgur.com/ajvKmORl.jpg)
![alt text](http://i.imgur.com/oHVZfIJl.jpg)
![alt text](http://i.imgur.com/gFbIz6fl.jpg)
