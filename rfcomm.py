client

"""
A simple Python script to send messages to a sever over Bluetooth 
using PyBluez (with Python 2).
"""

import bluetooth

serverMACAddress = '00:1a:7d:da:71:13'
port = 3
s = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
s.connect((serverMACAddress, port))
while 1:
	text = raw_input() # Note change to the old (Python 2) raw_input
	if text == "quit":
		break
	s.send(text)
sock.close()



server


"""
A simple Python script to receive messages from a client over 
Bluetooth using PyBluez (with Python 2). 
"""

import bluetooth 

hostMACAddress = '00:1A:7D:DA:71:13' # The MAC address of a Bluetooth adapter on the server. The server might have multiple Bluetooth adapters. 
port = 3 
backlog = 1
size = 1024
s = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
s.bind((hostMACAddress, port))
s.listen(backlog)
try:
	client, clientInfo = s.accept()
	while 1:
		data = client.recv(size)
		if data:
			print(data)
			client.send(data) # Echo back to client
except:	
	print("Closing socket")
	client.close()
	s.close()

    
    
    
    
    
    serve2
    
    import bluetooth

server_sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )

port = 0 # automatically choose port
server_sock.bind(("",port))
server_sock.listen(1)

uuid = "1e0ca4ea-299d-4335-93eb-27fcfe7fa848"
bluetooth.advertise_service( server_sock, "FooBar Service", uuid )

client_sock,address = server_sock.accept()
print "Accepted connection from ",address

data = client_sock.recv(1024)
print "received [%s]" % data

client_sock.close()
server_sock.close()
