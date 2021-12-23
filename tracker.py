import bencodepy
import socket 
import peer
import math
import _thread
# uses the formatted URL from the torrent and sends the HTTP GET request
# will receive back the bencoded dictionary response from tracker

class Tracker(object):
    def __init__(self, torrent):
        self.torrent = torrent
        self.response: str = ''
        self.response_len: int = 0
        self.complete : int = 0
        self.incomplete: int = 0
        self.interval: int = 0
        self.peers = []
        self.compact = False
        self.listening_socket = None

    def main(self, compact):
        if compact:
            self.compact = True
        if(self.torrent.announce.startswith("http")):
            self.http_client_to_tracker(self.torrent)
        elif(self.torrent.announce.startswith("udp")):
            self.udp_client_to_tracker(self.torrent)

    def get_compact(self):
        if self.compact is True:
            return 1
        else:
            return 0

    def printIP(self, ip_address):
        return str(ip_address[0]) + "." + str(ip_address[1]) + "." + str(ip_address[2])+ "." + str(ip_address[3]).strip()

    def http_client_to_tracker(self,torrent):
        # port is in range of 6881 to 6889
        params = {
            'info_hash': torrent.info_hash,
            'peer_id': torrent.peer_id,
            'uploaded': 0,
            'downloaded': 0,
            'port': 6881,
            'left': torrent.file_length,
            'event': 'started',
            'compact': self.get_compact()
        }
        
        
        # Grab the torrent announce and split it so we can grab the ip address 
        arr = torrent.announce.split("/")
        trunc_url = arr[2][:-5]
        trunc_announce = arr[3]
        ip_addy = socket.gethostbyname(trunc_url)

        
        #print(target_host)
        target_port = 6969
        # Create socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except:
            print("Was not able to create the socket")

        # now connect the client to the tracker
        try:
            sock.connect((str(ip_addy),target_port))
        except:
            print("Connect failed")
        self.our_ip_addr = sock.getsockname()[0]
        
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening = False
        while not listening:
            try:
                self.listening_socket.bind((self.our_ip_addr, params['port']))
                self.listening_socket.listen(25)
                listening = True
            except:
                print("Could not bind to the port: " ,params['port'])
                params['port'] += 1
        print("Listening for connections on port ", params['port'])

        # This target host will be passed into the request 
        # Formatted this way as we got it from wireshark
        target_host = trunc_announce
        target_host += "?info_hash=" + params['info_hash'] + "&peer_id=" + params['peer_id']
        target_host += "&port=" + str(params['port']) + "&event=" + params['event'] + "&left=" + str(params['left'])
        target_host += "&uploaded=" + str(params['uploaded']) + "&downloaded=" + str(params['downloaded'])
        target_host += "&compact=" + str(params['compact'])
        if self.compact:
            target_host += "&no_peer_id=1"
        else:
            target_host += "&no_peer_id=0"
        target_host+="&ip=" + self.our_ip_addr#THIS IS WHAt we NEED TO FIGURE OUT FOR EVERYTHING TO WORK
        self.our_port = params['port']

        # send some data 
        request = "GET /%s HTTP/1.1\r\nHost:%s:%s\r\n\r\n" % (target_host, str(ip_addy), str(target_port))
        sock.send(request.encode())  

        # receive some data 
        response = sock.recv(4096)  
        
        self.response = response
        self.response_len = len(response)
        response_split = response.split(b'\r\n\r\n')
        response_decode = bencodepy.decode(response_split[1])
        self.complete = response_decode[b'complete']
        self.incomplete = response_decode[b'incomplete']
        self.interval = response_decode[b'interval']

        if self.compact or type(response_decode[b'peers']) is not list:
            # compact format -> peers are stored in a byte string
            if len(response_decode[b'peers']) % 6 != 0:
                print("Uh oh spaghettio! invalid peer format received")
                exit(1)
            print("\nReceived " + str(math.floor(len(response_decode[b'peers'])/6)) + " peers")
            for i in range(math.floor(len(response_decode[b'peers'])/6)):
                peer_ip = response_decode[b'peers'][i*6:(i*6+4)]
                peer_ip = self.printIP(peer_ip)
                peer_port = int.from_bytes(response_decode[b'peers'][i*6 + 4:i*6+6], "big")
                
                # print("Checking for self connection '", peer_ip ,"' '", self.our_ip_addr,"'")
                if not self.contains_ip_port(self.peers, peer_ip, peer_port) and not (peer_ip == self.our_ip_addr and peer_port == self.our_port):
                    self.peers.append(peer.Peer(peer_ip, peer_port, None, self.torrent.number_of_pieces))
                # else:
                    # print("It was a duplicate or US")
        else:
            # non-compact format -> peers are stored in a list of dictionaries
            # retrieve the list
            peer_dict = response_decode[b'peers']
            # iterate thru the list of peers
            for p in peer_dict:
                peer_id = p[b'peer_id']
                peer_ip = p[b'ip']
                peer_port = p[b'port']
                # print("Checking for duplicates of '", peer_ip,"' ")
                # check if peer exists in client's peer list before adding
                if not self.contains_ip_port(self.peers, peer_ip, peer_port) or not (peer_ip == self.our_ip_addr and peer_port == self.our_port):
                    self.peers.append(peer.Peer(peer_ip, peer_port, peer_id, self.torrent.number_of_pieces))

        
    
    def udp_client_to_tracker(torrent):
        return
        
    def contains_ip_port(self, peers, peer_ip, peer_port):
        for peer in peers:
            if peer.ip_address == peer_ip and peer.port == peer_port:
                return True
        return False
    
