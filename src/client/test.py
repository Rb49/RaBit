import miniupnpc


def forward_port(port):
    upnp = miniupnpc.UPnP()
    upnp.discoverdelay = 200
    upnp.discover()
    upnp.selectigd()
    external_ip = upnp.externalipaddress()
    print("External IP address:", external_ip)
    upnp.addportmapping(port, 'TCP', upnp.lanaddr, port, 'Forwarded port', '')


if __name__ == "__main__":
    port_to_forward = 8080  # Change this to the desired port
    forward_port(port_to_forward)
