# RaBit
## A BitTorrent Client
### Features

- [x] http and udp trackers + compact response support (BEP 3, BEP 7, BEP 15, BEP 23)
- [x] download a multi-file torrent using all strategies (BEP 3, BEP 20)
- [x] download multiple torrents simultaneously
- [x] seeding 
- [x] tracker updating in intervals
- [x] smart ban 
- [x] canonical peer priority for seeding (BEP 40)
- [ ] user interface
- [x] upnp port forwarding with randomization

### Limitations
You won't be able to:

- use protocol extensions
- seed in ipv6
- download / seed without an upnp-enabled router or from a double nat
- download from magnet links (perhaps with an existing service api)
- contribute to incoming connections during download (only to outgoing)
