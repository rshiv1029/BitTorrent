import bencodepy
import math
from codecs import decode, register_error
from hashlib import sha1
from os.path import isfile
from random import choice
from re import search
from string import ascii_lowercase, digits
from socket import gethostbyname



# Error handler for the decode in percent encoding
def my_handler(exception):
        return '%', exception.end

register_error('my_handler', my_handler)

class Torrent(object):
    def __init__(self):
        self.torrent_file = {}
        self.name = b''
        self.file_length: int = 0
        self.piece_length: int = 0
        self.pieces: int = 0
        self.info_hash: str = ''
        self.info_hash_bytes = bytes(20)
        self.peer_id: str = ''
        self.announce = ''
        self.number_of_pieces: int = 0
        self.torrent = ''
        # self.url = ''

    def main(self, filename):
        torrent = filename

        # Check if the file exists
        if(not isfile(torrent)):
            print("Your file does not exist. Try again\n")
            exit()

        # Grab the string thats in the torrent file
        f = open(torrent, 'rb')
        torr = f.read()
        # Decode the torr string
        # This will Bdecode and parse the information into a dictionary d 
        data = bencodepy.decode(torr)
        

        # Populate the Torrent object
        self.torrent_file = data
        self.name = self.torrent_file[b'info'][b'name']
        self.file_length = self.torrent_file[b'info'][b'length']
        self.piece_length = self.torrent_file[b'info'][b'piece length']
        self.pieces = self.torrent_file[b'info'][b'pieces']
        self.number_of_pieces = math.ceil(self.file_length / self.piece_length)
        self.announce = self.torrent_file[b'announce'].decode('utf-8')
        # Grab the info from the dictionary and hash it
        # Also convert it to %nn format
        # Test encoding with print(percent_encoded('123456789a'))
        hashed_info = str(self.percent_encoded(sha1(bencodepy.bencode(data[b'info'])).hexdigest()))
        self.info_hash = hashed_info
        self.info_hash_bytes = bytearray(sha1(bencodepy.bencode(data[b'info'])).digest())
        # print("hashed_info: ", hashed_info)
        
        peer_id = str(self.generate_peer_id())
        self.peer_id = peer_id
        
        # peer_id = percent_encoded(peer_id)
        # print("peer_id: ", peer_id)


    def percent_encoded(self,string_in):
        final_str = ''
        i = 0
        while i < len(string_in)-1:
            temp = string_in[i:i+2]
            ascii_str = bytearray.fromhex(temp).decode('utf8', errors='my_handler')
            
            match = search('[A-Za-z0-9-_.~]', ascii_str)
            if (match == None):
                temp = "%"+temp
                temp = temp.upper()
                final_str += temp
            else:
                final_str += ascii_str
            i += 2
        return final_str
    
    # Python 2 Implementation 
    # def percent_encoded(str):
    #     final_str = ''
    #     i = 0
    #     while i < len(str)-1:
    #         temp = str[i:i+2]
    #         ascii_str = decode(temp, "hex")
    #         match = search('[A-Za-z0-9-_.~]',ascii_str)
    #         if (match == None):
    #             temp = "%"+temp
    #             temp = temp.upper()
    #             final_str += temp
    #         else:
    #             final_str += ascii_str
    #         i += 2
    #     return final_str

    def generate_peer_id(self):
        # generates a peer_id in the Azureus-style convention
        # "-" (dash) followed by 2 Client ID chars and 4 ASCII characters for version number followed by another "-" (dash) and 8 random characters 
        s = '-LOCALS-'
        #s = '-TR3000-'
        for x in range(0,12):
            s += str(choice(ascii_lowercase + digits))
        return s