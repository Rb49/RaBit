import upnpclient
import socket


def forward_port_upnp(external_port: int, internal_port: int, protocol: str, lease_duration: int = 3600, nat_ip: str = None) -> bool:
    """
    attempt to forward a port using UPNP protocol
    note: if called again too shortly, a conflict exception will be raised
    :param external_port: port accessible from outside the NAT
    :param internal_port: port accessible in this machine
    :param protocol: 'TCP' or 'UDP'
    :param lease_duration: for how long should the router remember the mapping rule? default is 1 hour
    :param nat_ip: this machine's ip. if 'None', it will be acquired
    :return: whatever the operation was successful.
    """

    if not nat_ip:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 53))  # some address
        nat_ip = s.getsockname()[0]
        s.close()

    devices = upnpclient.discover()

    success = False
    for d in devices:
        try:
            d.WANIPConn1.AddPortMapping(NewRemoteHost='0.0.0.0',
                                        NewExternalPort=external_port,
                                        NewProtocol=protocol,
                                        NewInternalPort=internal_port,
                                        NewInternalClient=nat_ip,
                                        NewEnabled='1',
                                        NewPortMappingDescription=f'RaBit ({protocol})',
                                        NewLeaseDuration=lease_duration)
            success = True
        except AttributeError:
            pass

    return success
