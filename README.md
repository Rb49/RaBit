# RaBit
## A pure Python asynchronous BitTorrent Client
### Features

- [x] http and udp trackers + compact response support (BEP 3, BEP 7, BEP 15, BEP 23)
- [x] download a multi-file torrent using all strategies (BEP 3, BEP 20)
- [x] download multiple torrents simultaneously
- [x] seeding
- [x] tracker updating in intervals
- [x] smart ban 
- [x] canonical peer priority for seeding (BEP 40)
- [x] user interface
- [x] upnp port forwarding with randomization
- [ ] cross-platform

### Limitations
You won't be able to:

- use protocol extensions
- seed in ipv6
- download / seed without an upnp-enabled router or seed from a double nat
- download from magnet links
- contribute to incoming connections during download (only to outgoing)

### Usage
1. go to `src` directory with ```cd RaBit/src```
2. install required libraries with ```pip install -r requirements.txt```
3. run `main.py`