import math
import socket
from threading import local
from time import time

KEEP_ALIVE_TIME = 120
class Peer: 
    def __init__(self, ip_address, port, peer_id, num_pieces):
        self.ip_address = ip_address
        self.port = port
        self.peer_id = peer_id 
        self.am_choking = True
        self.am_interested = False
        self.is_choking = True #not sure what to assume here
        self.is_interested = False
        self.num_pieces = num_pieces
        self.bitfield = bytearray(math.ceil(num_pieces/8))
        self.socket :socket.socket= None   
        self.upload_rate = 0
        self.last_keep_alive = None
        self.kill = False
        self.requestQueue = []
        #print("The type of IP adress is: ")
        #print(type(self.ip_address))

        #print("^^^^^^^^^^^^")

    def __str__ (self):
        toString = "\nPeerID: "
        if self.peer_id == None:
            toString += "None"
        toString += "\nIP address: " + self.printIP()
        toString += "\nPort: " + str(self.port) + "\n"
        #toString += 
        return toString

    #converts the bytes storing the ip address into dotted quad form 
    def printIP(self):
        #return str(self.ip_address[0]) + "." + str(self.ip_address[1]) + "." + str(self.ip_address[2])+ "." + str(self.ip_address[3])
        return str(self.ip_address)
   
    
    #call this function when a keep alive message is received
    def update_keep_alive(self):
        self.last_keep_alive = time()

    #call this function when a have message is received
    def update_piece(self,index): 
        self.bitfield[math.floor(index/8)] |= 0x80 >> (index % 8)

    #returns true if this peer has a specific piece
    def has_piece(self,index):
        return self.bitfield[math.floor(index/8)]&(0x80 >> (index % 8)) > 0

    #returns true if this peer can supply 
    def can_supply_piece(self, index): 
        return not self.is_choking and self.has_piece(index)

    #attempts to initiate a connection with this peer
    def start_connection(peer, infohash, client_id, locals):
        # print("Attempting to connect to: ", peer)
        try:
            peer.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer.socket.connect((peer.printIP(), peer.port))
            print("Connection succeeded to ", peer)
        except:
            print("Connection failed to ", peer)
            peer.socket = None
            exit()
        handshake_message = bytearray(29 + 19 + 20 )#first send 
        handshake_message[0] = 0x13#sets first byte to the decimal number 19
        handshake_message[1:20] = b'BitTorrent protocol'
        handshake_message[28:48] = infohash
        handshake_message[48:68] = client_id
        #print("Sent the following message: " , handshake_message)
        peer.socket.send(handshake_message)
        # print("waiting for response from: ", peer.ip_address)
        response = peer.socket.recv(29 + 19 + 20)
        # print("Received response from: ", peer.ip_address)
        #print("Here is the response: " , response)
        if(len(response) <= 0):
            peer.socket = None
            # print("The handshake was unsuccessful!")
            return
        if len(response) == 68:#validating handshake
            if response[0:20] != b'\x13BitTorrent protocol':
                print("This peer is running the wrong protocol")
                peer.socket = None
                return
            if response[20:28] != b'\x00\x00\x00\x00\x00\x00\x00\x00':
                print("Warning: this peer has set flags we don't understand")
            if response[28:48] != infohash:
                print("This peer sent the incorrect infohash")
                peer.socket = None
                return
            if peer.peer_id == None:
                peer.peer_id = response[48:68]
            elif response[48:68] != peer.peer_id:
                print("This peer had an unexpexted peer ID")
                peer.socket = None
                return
            if peer.peer_id[0:8] == b'-LOCALS-':
                # these are our clients
                print("Local Gang")
            elif locals:
                # not our clients, but we only want to connect to locals -> delete socket
                #print("We only want our clients thoooo")
                peer.socket = None
                return
        else :
            print("In start_connection, unsure how to handle a response of length ", len(response))
        peer.update_keep_alive() #updating the keep alive
        #
        # print("The handshake was successful!")


    #returns true if connection has been kept alive and false otherwise
    def has_valid_connection(peer):
        return peer.socket != None and time() - peer.last_keep_alive < KEEP_ALIVE_TIME


    def handle_bitfield(self, bitfield):
        if(len(bitfield) == len(self.bitfield)):
            self.bitfield = bitfield
            # print("Received this bitfield: ", self.bitfield)
            # print("Successfully set bitfield")

    def send_keep_alive(peer):
        message = bytearray(4)#this is the entire message
        try: 
            peer.socket.send(message)
            # print("you have been kept alive")
        except:
            print("uh oh spaghettio in send keep alive")
            peer.socket = None


    def choke(peer):
        if not peer.am_choking:
            peer.am_choking = True
            message = bytearray(5)#this is the entire message
            message[3] = 0x01
            message[4] = 0x00 #unnecessary line
            try: 
                peer.socket.send(message)
            except:
                print("uh oh spaghettio in choke")
                peer.socket = None


    def unchoke(peer):
        if peer.am_choking:
            peer.am_choking = False
            message = bytearray(5)#this is the entire message
            message[3] = 0x01
            message[4] = 0x01 
            try: 
                peer.socket.send(message)
            except:
                print("uh oh spaghettio in unchoke")
                peer.socket = None

    def set_interested(peer):
        if not peer.am_interested:
            peer.am_interested = True
            message = bytearray(5)#this is the entire message
            message[3] = 0x01
            message[4] = 0x02 
            try: 
                peer.socket.send(message)
                # print("Successfully sent interested message")
            except:
                print("uh oh spaghettio in set interested")
                peer.socket = None

    def set_not_interested(peer):
        if peer.am_interested:
            peer.am_interested = False
            message = bytearray(5)#this is the entire message
            message[3] = 0x01
            message[4] = 0x03 
            try: 
                peer.socket.send(message)
            except:
                print("uh oh spaghettio in set not interested")
                peer.socket = None

    def send_have(peer, index):
        if peer.am_interested:
            peer.am_interested = False
            message = bytearray(9)#this is the entire message
            message[3] = 0x05
            message[4] = 0x04
            message[5:9] = index.to_bytes(4,"big")
            try: 
                peer.socket.send(message)
            except:
                print("uh oh spaghettio in set send have")
                peer.socket = None

    def send_bit_field(self, bitfield):
        message = bytearray(math.ceil(self.num_pieces/8) + 5)
        message[0:4] = (math.ceil(self.num_pieces/8) + 1).to_bytes(4, "big")
        message[4] = 0x05
        message[5:(math.ceil(self.num_pieces/8) + 5)] = bitfield
        try: 
            self.socket.send(message)
        except:
            print("uh oh spaghettio in send bit field")
            self.socket = None
    
    def request(self, piece, offset, length):
        message = bytearray(17) #this is the entire message
        message[3] = 0x0D
        message[4] = 0x06
        message[5:9] = piece.to_bytes(4, "big")
        message[9:13] = offset.to_bytes(4, "big")
        message[13:17] = length.to_bytes(4,"big")
        try: 
            self.socket.send(message)
            print("\nSuccessfully sent request to " , self.printIP(), " for piece ", piece, " with offset ", offset)
        except:
            print("uh oh spaghettio in send request")
            self.socket = None
    
    def piece(self, index, begin, block):
        length = 9 + len(block)
        message = bytearray(length+4)
        message[0:4] = length.to_bytes(4, "big")
        message[4] = 0x07
        message[5:9] = index.to_bytes(4, "big")
        message[9:13] = begin.to_bytes(4, "big")
        message[13:] = block #block of data

        try: 
            self.socket.send(message)
        except:
            print("uh oh spaghettio in send piece")
            self.socket = None

    def check_interest(self, bitfield): 
        for i in range(self.num_pieces):
            if self.has_piece(i) and bitfield[math.floor(i/8)]&(0x80 >> (i % 8)) == 0:# they have a piece we dont
                if not self.am_interested:
                    self.set_interested()
                return
        if self.am_interested:
            self.set_not_interested()
    

    def findIndexOfRequest(self, req, requestQueue):
        for index in range(len(requestQueue)):
            request = requestQueue[index]
            if (req.piece == request.piece) and (req.offset == request.offset) and (req.length == request.length):
                return index
        print("uh oh spaghettio, couldn't find request in queue")
        exit()