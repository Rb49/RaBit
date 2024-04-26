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
- download many torrents at once (for now)
- seed in ipv6
- download / seed without an upnp-enabled router or from a double nat
- download from magnet links (perhaps with an existing service api)
- contribute to incoming connections during download (only to outgoing)

### Usage (without UI)
> [!IMPORTANT]
> 1. to mitigate unexpected behavior, use python version `3.10`
> 2. install requirements with ```pip install -r requirements.txt```
> 3. rename module name in `.idea/workspace.xml` to `RaBit`
> 4. run `src/client/main.py` from `RaBit/` directory
