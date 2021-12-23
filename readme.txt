Organization of Files
starter.py -> creates the torrent structure and parses in metainfo
torrent.py -> uses parsed in metainfo to prepare URL for HTTP GET request to send to tracker
tracker.py -> sends GET request and parses the tracker's response
peer.py -> creates sockets for peer connections/handshake and stores peer data