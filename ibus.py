 #!/usr/bin/python

import time
import serial
import threading

# Base on
# https://github.com/TrentSeed/BMW_E46_Android_RPi_IBUS_Controller
# https://github.com/t3ddftw/DroidIBus

RADIO_DISPLAY_SIZE = 12

class IBUSService(object):

    # configuration
    port = "/dev/ttyUSB0"
    baudrate = 9600
    bytesize = serial.EIGHTBITS
    parity = serial.PARITY_EVEN
    stopbits = serial.STOPBITS_ONE
    rtscts = True
    timeout = .1
    writeTimeout = 0
    _handle = None

    @property
    def handle(self):
        return self._handle

    @handle.setter
    def handle(self, value):
        self._handle = value
        if value is not None:
            self.onIBUSready_callback()

    def __init__(self, onIBUSready_callback, onIBUSpacket_callback):
        self.onIBUSready_callback = onIBUSready_callback
        self.onIBUSpacket_callback = onIBUSpacket_callback
        
        self._stop = threading.Event()

    def start(self):
        """
        Initializes bi-directional communication with IBUS adapter via USB
        """
        try:
            self.handle = serial.Serial(self.port,
                                        baudrate=self.baudrate, 
                                        bytesize=self.bytesize, 
                                        parity=self.parity, 
                                        stopbits=self.stopbits, 
                                        rtscts=self.rtscts, 
                                        timeout=self.timeout, 
                                        writeTimeout=self.writeTimeout)
        except:
            print "Cannot access to serial port " + self.port
            return False

        """
        Starts listen service
        """
        while not self.stopped():
            if (self.handle.inWaiting() >= 5):
                data = self.handle.read(9999)
                self.process_bus_dump(data)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def shutdown(self):
        """
        Closes serial connection and resets handle
        """
        try:
            self.handle.flushInput()
            self.handle.flushOutput()
            self.handle.close()
        except (TypeError, Exception):
            pass

        self.handle = None

    def process_bus_dump(self, dump, index=0):
        """
        Processes bytes received from serial and parse packets
        ---------------------------------------------
        | Source ID | Length | Dest Id | Data | XOR |
        ---------------------------------------------
                             | ------ Length -------|
        """
        packets = []
        hex_dump = dump.encode("hex")

        while index < len(hex_dump):
            try:
                # construct packet while reading
                current_packet = ""

                # extract source id
                source_id = hex_dump[index:(index+2)]
                current_packet += source_id
                index += 2

                # extract length info
                length = hex_dump[index:(index+2)]
                current_packet += length
                total_length_data = int(length, 16)
                total_length_hex_chars = (total_length_data * 2) - 4
                index += 2

                # extract destination id
                destination_id = hex_dump[index:(index+2)]
                current_packet += destination_id
                index += 2

                # extract inner data
                data = hex_dump[index:(index+total_length_hex_chars)]
                current_packet += data
                index += total_length_hex_chars

                # extract xor checksum
                xor = hex_dump[index:(index+2)]
                current_packet += xor
                index += 2

                # confirm full packet exists
                expected_packet_length = (2 + 2 + 2 + total_length_hex_chars + 2)
                if current_packet.__len__() != expected_packet_length:
                    continue

                # create packet
                packet = IBUSPacket(source_id=source_id, length=length, destination_id=destination_id,
                                    data=data, xor_checksum=xor, raw=current_packet)

                # add packet if valid
                if packet.is_valid():
                    packets.append(packet)

            except Exception as e:
                print "Error processing bus dump: " + e.message
                print "Dump: " + hex_dump

            # process packets data
            self.process_packets(packets)

    def process_packets(self, packets, index=0):
        """
        Process packets []
        """
        while index < len(packets):
            # print details of received packet
            # print(packets[index])
            
            # call the callback
            self.onIBUSpacket_callback(packets[index])
            del(packets[index])

        return True

    def send(self, hex_value):
        """
        Writes the provided hex packet(s) to the bus
        """
        try:
            self.handle.write(hex_value.decode("hex"))
        except Exception as e:
            print "Cannot write to IBUS: " + e.message


class IBUSPacket(object):

    # instance variables
    source_id = None
    length = None
    destination_id = None
    data = None
    xor_checksum = None
    raw = None

    def __init__(self, source_id, length, destination_id, data, xor_checksum=None, raw=None):
        """
        Initializes packet object
        """
        self.source_id = source_id
        self.length = length
        self.destination_id = destination_id
        self.data = data
        self.xor_checksum = self.calculate_xor_checksum() if xor_checksum is None else xor_checksum
        self.raw = self.source_id + \
                   self.length + \
                    self.destination_id + \
                    self.data + \
                    self.xor_checksum if raw is None else raw
        return

    def is_valid(self):
        """
        Verifies packet information & XOR checksum
        """
        if self.source_id is None or self.destination_id is None \
                or self.data is None or self.xor_checksum is None:
            return False

        # XOR checksum calculation
        return self.xor_checksum == self.calculate_xor_checksum()

    def __str__(self):
        """
        Human-readable string representing packet data
        """
        return "IBUSPacket\nRaw = " + self.raw + "\n"\
               + "Source = " + self.get_device_name(self.source_id) + "\n"\
               + "Destination = " + self.get_device_name(self.destination_id) + "\n"\
               + "Data = " + self.data + "\n"

    @staticmethod
    def get_device_name(device_id):
        """
        Returns device name for provided id
        i.e. 50 - MFL Multi Functional Steering Wheel Buttons
        """
        device_names = {
            "00": "Body Module (Broadcast)",
            "08": "Sunroof Control",
            "18": "CDW - CDC CD-Player",
            "28": "Radio Controlled Clock",
            "30": "Check Control Module",
            "3b": "NAV Navigation/Video Module",
            "3f": "Diagnostic",
            "40": "Remote Control Central Locking",
            "43": "Menu Screen",
            "44": "Ignition, Immobiliser",
            "46": "Central Information Display",
            "50": "MFL Multi Functional Steering Wheel Buttons",
            "51": "Mirror Memory",
            "5B": "Integrated Heating And Air Conditioning",
            "60": "PDC Park Distance Control",
            "68": "RAD Radio",
            "6a": "DSP Digital Sound Processor",
            "72": "Seat Memory",
            "73": "Sirius Radio",
            "76": "CD Changer DIN size",
            "7f": "Navigation Europe",
            "80": "IKE Instrument Kombi Electronics",
            "9b": "Mirror Memory Second",
            "9c": "Mirror Memory Third",
            "a0": "Rear Multi Info Display",
            "a4": "Air Bag Module",
            "a8": "?????",
            "b0": "Speed Recognition System",
            "bb": "TV Module",
            "bf": "Global Broadcast",
            "c0": "MID Multi-Information Display Buttons",
            "c8": "TEL Telephone",
            "ca": "BMW Assist",
            "d0": "Light Control Module",
            "da": "Seat Memory Second",
            "e0": "Integrated Radio Information System",
            "e7": "OBC Text Bar",
            "e8": "Rain Light Sensor",
            "ed": "Lights, Wipers, Seat Memory",
            "f0": "BMB Board Monitor Buttons",
            "ff": "Broadcast",
        }

        try:
            return device_names[device_id]
        except KeyError:
            return "Unknown"

    def calculate_xor_checksum(self):
        """
        Calculates XOR value for packet
        """
        packet = [self.source_id, self.length, self.destination_id] \
                + [self.data[i:i+2] for i in range(0, len(self.data), 2)]

        checksum = 0x00
        for i in range(0, len(packet)):
            checksum ^= int(str(packet[i]), 16)

        return "{:02x}".format(checksum)


class IBUSCommands(object):

    ibus = None

    def __init__(self, IBUSService):
        # instance of IBUSService()
        self.ibus = IBUSService
        self._print_stop = threading.Event()

    def get_display_packet(self, str=None, state=None):
        """
        C8 0A 80 23 42 32 48 65 6C 6C 6F 53
        C8 - Telephon (sender)                  (1st byte is the Source ID)
        0A - 10 bait length                     (2nd byte is length of the packet excluding
                                                the first two bytes (source & length)
        80 - RAD (radio) destination            (3rd byte is the destination ID)
        23 - function 0x23 (printing?)          (4th byte onwards is the actual data)
        42 - to define the layout mode
        32 - to clear the display first
        48 65 6C 6C 6F - Hello
        53 - Checksum                           (Last byte is the checksum)
        """
        if state is None:
            str = str[:RADIO_DISPLAY_SIZE]
            length = len(str) + 5
            data = str.encode("hex")
        else:
            str = str[:RADIO_DISPLAY_SIZE-2]
            length = len(str) + 7
            if state == "connect":
                data = "c8"
            elif state == "mute":
            	data = "c6"
            elif state == "playing":
                data = "bc"
            else:
                data = "be"
            data += "20" + str.encode("hex")

        packet = IBUSPacket(source_id="c8", length="{:02x}".format(length), destination_id="80", data="234232" + data)
        return packet if packet.is_valid() else False
    
    def print_on_display(self, data=[]):
        for i in range(0, 10):
            time.sleep(.2)
            if self.print_stopped():
                return

        packet = self.get_display_packet(data[0])
        self.ibus.send(packet.raw)

        for i in range(0, 10):
            time.sleep(.2)
            if self.print_stopped():
                return
        
        for i in range(1, len(data[0])-RADIO_DISPLAY_SIZE+1):
            packet = self.get_display_packet(data[0][i:])
            self.ibus.send(packet.raw)

            time.sleep(.5)        
            if self.print_stopped():
                return

        # invert the list
        self.print_on_display(data[::-1])

    def print_clear(self):
        self._print_stop.clear()
    
    def print_stop(self):
        self._print_stop.set()

    def print_stopped(self):
        return self._print_stop.isSet()
        
    def set_clock(self):
        """
        GT telling IKE to set the time: 
        3B 06 80 40 01 0C 3B cc
        GT -> IKE : On-board computer set data: Set Time = 12:59
        40 = OBC Set data
        01 = Time
        0C = hours in hex
        3B = minutes in hex

        GT telling IKE to set the date: 
        3B 07 80 40 02 1B 05 08 cc
        GT -> IKE : On-board computer set data: Set Date = 27/05/08
        40 = OBC Set data 
        02 = Date
        1B = day in hex 
        05 = month in hex
        08 = year in hex
        
        time.strftime("%y-%m-%d %H:%M") '16-11-19 09:38'
        """
        # Time
        hour = "{:02x}".format(int(time.strftime("%H")))
        minute = "{:02x}".format(int(time.strftime("%M")))

        packet = IBUSPacket(source_id="3b", length="06", destination_id="80", data="4001" + hour + minute)
        self.ibus.send(packet.raw)

        # Date
        day = "{:02x}".format(int(time.strftime("%d")))
        month = "{:02x}".format(int(time.strftime("%m")))
        year = "{:02x}".format(int(time.strftime("%y")))

        packet = IBUSPacket(source_id="3b", length="07", destination_id="80", data="4002" + day + month + year)
        self.ibus.send(packet.raw)

    def request_for_ignition(self):
        """
        Request ignition status from the IKE
        IBUS Message: BF 03 80 10 2C
        @return
        0x01 - Pos1_Acc
        0x02 - Pos2_On
        0x03 - Pos3_Start
        """
        self.ibus.send("bf0380102c")

    def request_for_sensors(self):
        """
        IKE sensor status request
        IBUS Message: BF 03 80 12 2E
        """
        self.ibus.send("bf0380122e")
        
    def request_for_gong(self):
        """
        IBUS Message: BF 03 80 1a 26
        """
        self.ibus.send("bf03801a26")        
        
    def request_for_mileage(self):
        """
        Request mileage from the IKE
        IBUS Message: BF 03 80 16 2A
        @return 80 0A BF 17 DC 11 03 01 28 72 CC 7B (201 180 kms)
        Bytes 5-7 contain the Mileage in KMs
        Bytes 8 and 9 hold the inspection interval in KMs
        Byte 10 is the SIA Type (0x40 == Inspection)
        Byte 11 is the the days to inspection.
        """
        self.ibus.send("bf0380162a")

    def request_for_pdc(self):
        """

        """
        self.ibus.send("3f03601b47")

    def clown_nose_on(self):
        """
        It turns-on "clown nose" under back mirror for 3 seconds
        """
        self.ibus.send("3f05000c4e0179")
        
"""
3b 05 80 41 0a 10 chk - average speed delete
3b 06 80 40 09 00 xx chk - speed limits set (audio signal with exceeding)
3b 05 80 41 09 20 chk - speed limits on current speed set
3b 05 80 41 09 08 chk - deactivate adjusted speed limit
"""