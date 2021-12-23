from enum import Enum
from getopt import getopt, GetoptError
from hashlib import sha1
from random import randint
from sys import argv, exit, stdout
from threading import Thread, active_count
import math
from time import time
import request
import select
import socket
import torrent
import tracker
from peer import Peer

BLOCK_LENGTH = 2**14

class DownloadState(Enum):
    WAITING_FOR_HOPE = 0
    READY_TO_REQUEST = 1
    WAITING_FOR_RESPONSE = 2
    COMPLETE = 3


class startTorrent(object):
    def __init__(self):
        self.torrent = torrent.Torrent()
        self.tracker = tracker.Tracker(self.torrent)
        self.filename = ""
        self.seeder = False
        self.locals = False
        self.verbose = False
        self.keep_alive_time = time()
        self.request_time = time()
        
    def main(self, argv):
        torrent_path = ''
        compact = False
        try:
            opts, args = getopt(argv,"hcslt:",["tfile="])
        except GetoptError:
            print('test.py -t <torrentfile> -c')
            exit(2)
        for opt, arg in opts:
            if opt == '-h':
                print('starter.py -t <torrentfile> -c [-s] [-l]') 
                exit()
            elif opt in ("-t", "--tfile"):
                torrent_path = arg
            elif opt == '-c':
                compact = True
            elif opt == '-s':
                self.seeder = True 
            elif opt == '-l':
                self.locals = True

        # print("Torrent file is " + str(torrent_path))
        self.torrent.main(torrent_path)    
        self.tracker.main(compact)

        # for peer in self.tracker.peers:
        #     print(peer)
        self.connect_to_peers()
        #self.tracker.peers      
        self.remove_unconnected_peers()
        
        # print("Peer List after removing duplicates and bad connections:")
        # for peer in self.tracker.peers:
        #     print(peer)
        #for peer in self.tracker.peers:
            # Peer.send_keep_alive(peer)
            # print(peer)

        self.setup_piece_buffer()   #initializes many necessary variables
        while self.torrenting:
            self.check_messages()
            self.update_state()
            self.upload_one_block()#doesn't do anything yet
            self.handle_periodic_events()#doesn't do anything yet


    def setup_piece_buffer(self):
        self.num_pieces = self.torrent.number_of_pieces
        self.piece_len = self.torrent.piece_length
        # self.piece_buffer = [bytearray(self.piece_len)]*self.num_pieces
        self.piece_buffer = [bytearray(self.piece_len) for y in range(self.num_pieces)] 
        self.num_blocks = math.ceil(self.piece_len/BLOCK_LENGTH)
        self.num_blocks_in_last_piece = math.ceil(  (self.torrent.file_length - (self.num_pieces - 1)*self.piece_len) / BLOCK_LENGTH)
        self.bitfield = bytearray(math.ceil(self.num_pieces/8))
        self.cur_piece = -1
        self.cur_block = 0
        self.torrenting = True
        self.download_state = DownloadState.WAITING_FOR_HOPE # could switch to enum here to be fancy
        
    def update_state(self): #SHOULD ADD MORE SSTUFF HERE LATER I SUPPOSE
        # print("The current download state is: ", self.download_state)
        if self.download_state == DownloadState.WAITING_FOR_HOPE:
            if self.is_there_hope():
                if self.cur_piece == -1 or self.has_piece(self.cur_piece): #must pick new piece
                     self.pick_next_piece()
                self.request_cur_block_from_random_peer()
                self.download_state == DownloadState.WAITING_FOR_RESPONSE
        elif self.DownloadState == DownloadState.READY_TO_REQUEST:
            if self.cur_piece == -1 or self.has_piece(self.cur_piece): #must pick new piece
                self.pick_next_piece()
                # print("Picking a new piece cause we already have this one!")
            self.request_cur_block_from_random_peer()
            self.download_state == DownloadState.WAITING_FOR_RESPONSE
        elif self.download_state == DownloadState.COMPLETE:
            print("\nWe are done downloading!!!!")
        else:
            print("You're not in a correct state")
                #pick piece
                #request it
                #set state

    def has_piece(self,index):
        return self.bitfield[math.floor(index/8)]&(0x80 >> (index % 8)) > 0

    def peers_who_can_supply_piece(self, index):
        supplier_list = []
        for peer in self.tracker.peers:
            if peer.can_supply_piece(index):
                supplier_list.append(peer)
        return supplier_list

    def request_cur_block_from_random_peer(self):
        #MAY FAIL SO ACCOUNT FOR THAT LATER
        peer = 0
        peers = self.peers_who_can_supply_piece(self.cur_piece)

        if(len(peers) > 0):
            r = randint(0, len(peers) - 1) 
            peer = peers[r] 
            # print("Randomly selected peer: ", r)
        else:
            # print("NOT HANDLED THIS WILL CAUSE A RUNTIME ERROR")
            exit() 

        if(self.cur_piece == self.num_pieces - 1 and self.cur_block == self.num_blocks_in_last_piece -1):
            peer.request(self.cur_piece, self.cur_block*BLOCK_LENGTH,\
            self.torrent.file_length - (self.num_pieces - 1)*self.piece_len - (self.num_blocks_in_last_piece - 1)*BLOCK_LENGTH)#for last block, length is different
        else:    
            peer.request(self.cur_piece, self.cur_block*BLOCK_LENGTH, BLOCK_LENGTH)

    def pick_next_piece(self):#change to rarest first later
        """ for i in range(self.num_pieces):
            if not self.has_piece(i) and len(self.peers_who_can_supply_piece()) > 0 :
                self.cur_piece = i
                self.cur_block = 0 """
        # choose piece held by the lowest num of peers
        peer_counter = []
        for i in range(self.num_pieces):
            if not self.has_piece(i):
                peer_counter.append(len(self.peers_who_can_supply_piece(i)))
            else:
                peer_counter.append(100000)
        # set piece to the lowest held one
        if min(peer_counter) == 100000:#no pieces available
            # print("WOW UH OH")
            exit()
        self.cur_piece = peer_counter.index(min(peer_counter))
        self.cur_block = 0
        

    def connect_to_peers(self):
        threads = []
        for P in self.tracker.peers:
            #try:
                my_thread = Thread( target=Peer.start_connection, 
                                    args=[P, self.torrent.info_hash_bytes,self.torrent.peer_id.encode(), self.locals]
                                )
                threads.append(my_thread)
                # print("# of active threads: ", len(threads))
            #except:
            #    print("Thread failed")
            # peer.start_connection(self.torrent.info_hash_bytes,self.torrent.peer_id.encode())
        for t in threads:
            t.start()
            

        for t in threads:
            t.join()

    def remove_unconnected_peers(self):
        for index in reversed(range(len(self.tracker.peers))):
            if self.tracker.peers[index].socket == None:
                self.tracker.peers.remove(self.tracker.peers[index])

    def check_messages(self):
        socket_list = [self.tracker.listening_socket]
        for peer in self.tracker.peers:
            if peer.socket != None:
                socket_list.append(peer.socket)
            
        # print("awaiting new message:") 
        ready_sockets, a, b = select.select(socket_list, [], [])#timeout should be set to 0 IFF we have people waiting for downloads
        
        for ready_socket in ready_sockets:
            if ready_socket == self.tracker.listening_socket:
                # print("We have a new connection trying ")
                new_socket = None
                address = None
                response = None
                try:
                    new_socket, address = ready_socket.accept()
                     # Possible issue with reading immeadiately after but maybe not? 
                    response = new_socket.recv(29 + 19 + 20)
                    # print("Response: ", response)
                except:
                    print("uh oh spaghettio in accept")
                    continue
                
                 # Validate the handshake
                if len(response) == 68:
                    if response[0:20] != b'\x13BitTorrent protocol':
                        print("This peer is running the wrong protocol")
                        continue
                    if response[20:28] != b'\x00\x00\x00\x00\x00\x00\x00\x00':
                        print("Warning: this peer has set flags we don't understand")
                    if response[28:48] != self.torrent.info_hash_bytes:
                        print("This peer sent the incorrect infohash")
                        continue
                else:
                    continue
                peer_id = response[48:68]
                
                handshake_message = bytearray(29 + 19 + 20 ) # message back 
                handshake_message[0] = 0x13 # sets first byte to the decimal number 19
                handshake_message[1:20] = b'BitTorrent protocol'
                handshake_message[28:48] = self.torrent.info_hash_bytes
                handshake_message[48:68] = self.torrent.peer_id.encode()
                new_socket.send(handshake_message)
                new_peer = Peer(address[0], address[1], peer_id, self.num_pieces)
                new_peer.socket = new_socket
                new_peer.update_keep_alive()
                new_peer.send_bit_field(self.bitfield)
                new_peer.unchoke()#REALLY SHOULD NOT DO THIS HERE
                self.tracker.peers.append(new_peer)


                # print("WE HAVE ACCEPTED OUT FIRST PEER!!")
            else:
                for peer in self.tracker.peers:
                    if peer.socket == ready_socket:
                        message_len_bytes = peer.socket.recv(4)#maybe wrap this in a try one day?
                        if(len(message_len_bytes) == 0):#They want to terminate the connection
                            peer.kill = True
                        message_len = int.from_bytes(message_len_bytes,"big")

                        print("We received a new message from ", peer.printIP(), " of length ", message_len)
                        #if(length )
                        if(message_len == 0):#this is a staying alive message
                            peer.update_keep_alive()
                            # print("Received keeping alive message")
                        else: 
                            message_body = bytearray()
                            while len(message_body) < message_len:
                                new_body = (peer.socket.recv(message_len - len(message_body)))
                                if new_body:
                                    message_body.extend(new_body)
                            # print(len(message_body))    
                            message_code = message_body[0]
                            print("This message has code: ", message_code)
                        # HANDLING OUR POSSIBLE MESSAGES BASED ON CODES
                            # HANDLE CHOKE
                            if message_code == 0:
                                peer.is_choking = True
                                print("We got choked")
                            # HANDLE UNCHOKE
                            elif message_code == 1:
                                peer.is_choking = False
                                print("We got unchoked") 
                            # HANDLE INTERESTED
                            elif message_code == 2:
                                peer.is_interested = True
                            # HANDLE UNINTERESTED
                            elif message_code == 3:
                                peer.is_interested = False
                            # HANDLE HAVE
                            elif message_code == 4:
                                peer.handle_have(int.from_bytes(message_body[1:5]))
                                peer.check_interest(self.bitfield)                            
                            # HANDLE BITFIELD
                            elif message_code == 5:
                                peer.handle_bitfield(message_body[1: message_len])
                                peer.check_interest(self.bitfield)
                            # HANDLE REQUEST (CHECK CODE)
                            elif message_code == 6:
                                piece = int.from_bytes(message_body[1:5], "big")
                                begin = int.from_bytes(message_body[5:9], "big")
                                length = int.from_bytes(message_body[9:13], "big")
                                # print("Have parsed request baby index= ", index, " begin= ", begin, "length= ", length)
                                if not peer.am_choking and self.has_piece(piece):
                                    req = request.Request(piece, begin, length)
                                    peer.requestQueue.append(req)   
                                else:
                                    print("We can't help we're choking you")                   
                            # HANDLE PIECE
                            elif message_code == 7:
                                piece = int.from_bytes(message_body[1:5], "big")
                                block = int.from_bytes(message_body[5:9], "big")
                                # print("Have received part of the file baby piece= ", piece, " block=", block)
                                if block/BLOCK_LENGTH == self.cur_block:
                                    self.piece_buffer[piece][block:block + message_len - 9] = \
                                    message_body[9:message_len]# SHOULD CHECK THAT LENGTH MATCHS
                                    # print(self.piece_buffer[piece][block:block + message_len - 9])
                                    
                                    if(self.cur_block == self.num_blocks-1 or (self.cur_piece == self.num_pieces - 1 and self.cur_block == self.num_blocks_in_last_piece - 1)):
                                        print("Finished downlading piece ", self.cur_piece, " to the buffer")
                                        self.verify_piece(self.cur_piece)
                                        self.finished_cur_piece()
                                        
                                        # self.torrenting = False # Just to end after one piece REMOVE LATER
                                    else:
                                        # print("PIECE IS NOT DONE")
                                        self.cur_block += 1
                                        self.DownloadState = DownloadState.READY_TO_REQUEST                            
                            # HANDLE CANCEL (CHECK CODE)
                            elif message_code == 8:
                                piece = int.from_bytes(message_body[1:5], "big")
                                offset = int.from_bytes(message_body[5:9], "big")
                                length = int.from_bytes(message_body[9:13], "big")

                                # find the index of the request in the peer's requestQueue and pop it off
                                if len(peer.requestQueue) > 0:
                                    for index in reversed(range(len(peer.requestQueue))):
                                        req = peer.requestQueue[index]
                                        if req.piece == piece and req.offset == offset and req.length == length:
                                            peer.requestQueue.remove(req)
                self.remove_dead_peers()

    def remove_dead_peers(self):
        for index in reversed(range(len(self.tracker.peers))):
            if self.tracker.peers[index].kill:
                # print("Killing peer with ID ", self.tracker.peers[index].printIP())
                self.tracker.peers.remove(self.tracker.peers[index]) 
        # print("Killed all dead peers")

    def upload_one_block(self):
        # return
        index = 0
        unchoked_peers = []
        for peer in self.tracker.peers:
            if not peer.am_choking and len(peer.requestQueue) > 0:
                unchoked_peers.append(peer)
        # print(len(unchoked_peers))
        if len(unchoked_peers) == 0:
            return
        else:
            index = randint(0, len(unchoked_peers) - 1)
            peer = unchoked_peers[index]
            # Grab the request that we want to handle
            req = peer.requestQueue.pop()
            
            # NOT DONE YET
            block_to_send = self.piece_buffer[req.piece][req.offset:req.offset+req.length]
            peer.piece(req.piece, req.offset, block_to_send)


    def handle_periodic_events(self):
        curr_time = time()
        diff_keep_alive = curr_time - self.keep_alive_time
        diff_request = curr_time - self.request_time
        if diff_keep_alive > 120.0:
            for peer in self.tracker.peers:
                Peer.send_keep_alive(peer)
                self.keep_alive_time = time()
        # if diff_request > self.tracker.interval:
        #     self.tracker = self.tracker.main(compact)

    # Goal: We want to veify that the piece we grab from the piece buffer has a matching hash that is provided in the initial torrent file  
    def verify_piece(self, index):
        # Grab the correct piece from the torrent file
        torrent_piece = self.torrent.pieces[index*20:(index*20+20)]
        last_piece_bytes = (self.torrent.file_length - (self.num_pieces - 1)*self.piece_len)
        if index == self.num_pieces-1:
            # Hash the piece that we index in our piece buffer
            hashed_piece = bytes(sha1(self.piece_buffer[index][0:last_piece_bytes]).digest())
            if hashed_piece != torrent_piece:
                print("uh oh spaghettio, piece " + str(index) + "in buffer doesnt match torrent piece")
                exit()
        else:
            # Hash the piece that we index in our piece buffer
            hashed_piece = bytes(sha1(self.piece_buffer[index]).digest())
            if hashed_piece != torrent_piece:
                print("uh oh spaghettio, piece " + str(index) + "in buffer doesnt match torrent piece")
                exit()
        # print("PIECE IS VERIFIED\n")

    def write_piece_buffer_to_file(self):
        filename = self.torrent.name.decode('utf-8')
        f = open(filename, "wb")
        bytes_read = 0
        for piece in self.piece_buffer:
            if self.piece_len + bytes_read < self.torrent.file_length:
                f.write(piece)
                bytes_read += self.piece_len
            else:
                bytes_left = self.torrent.file_length - bytes_read
                temp_arr = piece[0:bytes_left]
                f.write(temp_arr)
        f.close()

    def is_there_hope(self): #checks if there are pieces we need that we CAN get
        for peer in self.tracker.peers:
            if peer.am_interested and not peer.is_choking: # we can get shit from em
                return True
        return False

    def finished_cur_piece(self):
        self.bitfield[math.floor(self.cur_piece/8)] |= 0x80 >> (self.cur_piece % 8)
        self.print_progress()
        #now that our bitfield has changed, must recalculate interest in our peers
        for peer in self.tracker.peers:
            peer.check_interest(self.bitfield)

        if self.is_finished_downloading():
            self.write_piece_buffer_to_file()
            # if we are not a seeder, we can exit (torrenting = false)
            # print("Are we a seeder?", self.seeder)
            if not self.seeder:
                self.torrenting = False #may need to change later
            self.download_state = DownloadState.COMPLETE
        if self.is_there_hope():
            self.DownloadState = DownloadState.READY_TO_REQUEST
        else:
            self.DownloadState = DownloadState.WAITING_FOR_HOPE
    
    def is_finished_downloading(self):
        for i in range(self.num_pieces):
            if not self.has_piece(i):
                return False
        return True
    
    def percent_finished_downloading(self):
        count = 0
        for i in range(self.num_pieces):
            if self.has_piece(i):
                count += 1
        return math.floor((count/self.num_pieces)*100)

    def print_progress(self):
        percent_done = self.percent_finished_downloading()
        if percent_done%10 >= 5:
            percent_done += 10 - (percent_done%10)
        else:
            percent_done -= percent_done%10

        num_arrow = percent_done
        num_period = 100 - num_arrow
        bar = "["
        while num_arrow > 0:
            bar += ">"
            num_arrow -= 1
        while num_period > 0:
            bar += "."
            num_period -= 1
        bar += "]\n"
        stdout.write(bar)
        stdout.flush()
        # print(bar)
        
                              

 
if __name__ == "__main__":
    startTorrent = startTorrent()
    startTorrent.main(argv[1:])