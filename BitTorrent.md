# 1.1 Overview of bittorrent
## The bittorrent protocol has to two main parts.

### Step 1: 
You need to send a request to something called a tracker, and the tracker will respond with a list of peers. More specifically, you tell the tracker which files you’re trying to download, and the tracker gives you the ip address of the users you download them from. Making a request to a tracker also adds your ip address to the list of users that can share that file.

### Step 2: 
After you have the list of peer addresses, you want to connect to them directly and start downloading. This happens through an exchange of messages where they tell you what pieces they have, and you tell them which pieces you want.

# 1.2 Links and references
## These are links that may be helpful to understanding this project:

## [Unofficial Specification](wiki.theory.org/index.php/BitTorrentSpecification) 
This is an unofficial bittorrent specification but basically has everything you need to know. Detailed and very readable.

## [Official Specification](www.bittorrent.org/beps/bep_0015.html) 
The only thing thing you won’t find in the unofficial spec is how to form a request to a tracker that uses a UDP url. But you can find it here in this link. I’ll remind you about this link again when I cover trackers and UDP.

## [High Level Explanation 1](www.morehawes.co.uk/the-bittorrent-protocol) 
A very good high level explanation of the bittorrent protocol.

## [High Level Explanation 2](www.kristenwidman.com/blog/33/how-to-write-a-bittorrent-client-part-1)
Another good high level explanation.

## [BEP for Peer ID conventions](www.bittorrent.org/beps/bep_0020.html) 


# 1.3 Conventions
1. peer v/s client: In this document, a peer is any BitTorrent client participating in a download. The client is also a peer, however it is the BitTorrent client that is running on the local machine. Readers of this specification may choose to think of themselves as the client which connects to numerous peers.
2. piece v/s block: In this document, a piece refers to a portion of the downloaded data that is described in the metainfo file, which can be verified by a SHA1 hash. A block is a portion of data that a client may request from a peer. Two or more blocks make up a whole piece, which may then be verified.
3. defacto standard: Large blocks of text in italics indicates a practice so common in various client implementations of BitTorrent that it is considered a defacto standard.