# Import socket module
from socket import *
def reply(client_addr, msg):
    client_ip = client_addr[0]
    client_port = client_addr[1]
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.sendto(msg, (client_ip, client_port))
    clientSocket.close()

# Assign a port number
serverPort = 12000
# Create a UDP server socket
# (AF_INET is used for IPv4 protocols)
# (SOCK_DGRAM) is used for UDP
serverSocket = socket(AF_INET,SOCK_DGRAM)
# Bind the socket to server address and server port
serverSocket.bind(('127.0.0.1',serverPort))
print('The server is ready to receive')
# Server should be up and running and listening to the incoming connections
while 1:
    # Receives the request message from the client
    message, clientAddress = serverSocket.recvfrom(2048)
    print(message)
    capitalizedSentence = message.upper()
    #serverSocket.sendto(capitalizedSentence, clientAddress)
    reply(clientAddress, capitalizedSentence)