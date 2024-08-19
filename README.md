# RaBit
## A pure Python asynchronous BitTorrent Client
### Features

- [x] HTTP and UDP tracker announces + compact response support (BEP 3, BEP 7, BEP 12, BEP 15, BEP 23)
- [x] Download a multi-file torrent using all strategies (BEP 3, BEP 20)
- [x] Download multiple torrents simultaneously
- [x] Seeding + tracker updating in intervals
- [x] Smart ban 
- [x] Location-based peer filtering
- [x] Canonical peer priority for seeding (BEP 40)
- [x] UPnP port forwarding with randomization
- [x] User interface
- [x] Compatible with Windows / Linux / macOS

### Limitations
You won't be able to:

- Use protocol extensions
- Seed in ipv6
- Download / seed without an upnp-enabled router or seed from a double nat
- Download from magnet links
- Contribute to incoming connections during download (only to outgoing)

**And lastly, RaBit is as a learning project and not for production, so keep that in mind ;)**

### Usage and installation
> [!IMPORTANT]
> To mitigate unexpected behavior, use a python version equal or above `3.10`

1. Go to `src` directory with ```cd RaBit/src```
2. Install required libraries with ```pip install -r requirements.txt```
3. Run with GUI: `main.py`

   Run without GUI: `viewless.py` (with args: seed: bool, torrent_path: str, result_path: str, skip_hash_check: bool)

Running `reset.py` can be helpful with a file-related problem.

### Usage example
Downloading Linux Debian iso:
>
> https://github.com/Rb49/RaBit/assets/95938066/918fce2d-278e-4bba-b195-973a75534007

### Screenshots
Full screen in Windows:
> 
> ![windows_1080p_download](https://github.com/Rb49/RaBit/assets/95938066/6efe93dd-a2e1-404e-9039-3492e0d794fe)

Minimized screen in Windows:
>
> ![windows_1080p_minimized](https://github.com/Rb49/RaBit/assets/95938066/503dd815-e02e-46da-adc0-93fdf200165e)

Full screen in Kali-Linux:
> 
> ![linux_download](https://github.com/Rb49/RaBit/assets/95938066/80aef9e9-f2a8-45c0-bd86-c99fdf0e8cba)

Minimized screen in macOS:
>
> ![macos_download](https://github.com/Rb49/RaBit/assets/95938066/845b22f6-1375-429d-ba6e-8dde5db727a4)
