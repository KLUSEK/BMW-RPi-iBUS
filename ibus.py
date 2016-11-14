 #!/usr/bin/python

import serial

# Base on
# https://github.com/TrentSeed/BMW_E46_Android_RPi_IBUS_Controller
# https://github.com/t3ddftw/DroidIBus

RADIO_DISPLAY_SIZE = 12
#30 LEN 80 1A 35 00 TEXT CS

class IBUSService:

    # configuration
    baudrate = 9600
    handle = None
    parity = serial.PARITY_EVEN
    port = '/dev/ttyUSB0'
    timeout = 1

#    def __init__(self):
#        """
#        Initializes bi-directional communication with IBUS adapter via USB
#        """
#        try:
#            self.handle = serial.Serial(self.port, parity=self.parity, timeout=self.timeout, stopbits=1)
#            self.thread = threading.Thread(target=self.start)
#            self.thread.daemon = True
#            self.thread.start()
#        except:
#            print "Cannot access to serial port " + self.port

    def start(self):
        """
        Initializes bi-directional communication with IBUS adapter via USB
        """
        try:
            self.handle = serial.Serial(self.port, parity=self.parity, timeout=self.timeout, stopbits=1)
        except:
            print "Cannot access to serial port " + self.port
            return False
        
        """
        Starts listen service
        """
        while True:
            data = self.handle.read(9999)
            if len(data) > 0:
                self.process_bus_dump(data)

    def shutdown(self):
        """
        Closes serial connection and resets handle
        """
        try:
            print "Destroying IBUS service..."
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
                packet = IBUSPacket(source_id=source_id, length=total_length_data, destination_id=destination_id,
                                    data=data, xor_checksum=xor, raw=current_packet)

                # add packet if valid
                if packet.is_valid():
                    packets.append(packet)

            except Exception as e:
                print "Error processing bus dump: " + e.message

            # process packets data
            self.process_packets(packets)

    @staticmethod
    def process_packets(packets, index=0):
        """
        Process packets []
        """
        while index < len(packets):
            # print details of received packet
            # print(packets[index])

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


class IBUSPacket:

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
            "bf": "Global Broadcast Address",
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


class IBUSCommands:

    ibus = None

    def __init__(self, IBUSService):
        # instance of IBUSService()
        self.ibus = IBUSService        
        
    def generate_display_packet(self, str):
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
        53 - Checksume                          (Last byte is the checksum)
        """
        str = str[:RADIO_DISPLAY_SIZE]
        packet = IBUSPacket(source_id="c8", length="{:02x}".format(len(str)+5), \
                            destination_id="80", data="234232"+str.encode("hex"))

        return packet.raw if packet.is_valid() else False
    
    def clown_nose_on(self):
        """
        It turns-on "clown nose" under back mirror for 3 seconds
        """
        self.ibus.send("3f05000c4e0179")