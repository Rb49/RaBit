import src.app_data.db_utils as db_utils
from src.file.file_object import PickableFile

import socket
from typing import Union, Tuple, Dict
import time
import crc32c


FileObjects: Dict[bytes, PickableFile] = dict()


async def save_forward(internal_port: int, external_port: int, version: str) -> None:
    """
    saving a mapping configuration to thr config file
    :param internal_port: internal port on the machine
    :param external_port: external port on the rounter's external nic
    :param version: 'v4' for ipv4 | 'v6' for ipv6
    :return: None
    """
    if version == 'v4':
        await db_utils.set_configuration(
            'v4_forward', {
                'internal_port': internal_port,
                'external_port': external_port,
                'last_forward': time.time()}
        )
    else:  # version == 'v6'
        await db_utils.set_configuration(
            'v6_forward', {
                'internal_port': internal_port,
                'external_port': external_port,
                'last_forward': time.time()}
        )


def load_forwarding(version: str) -> Tuple[int, int, float]:
    """
    loads a previous port mapping configuration
    :param version: 'v4' for ipv4 | 'v6' for ipv6
    :return: internal port, external port, last forward time
    """
    if version == 'v4':
        values = db_utils.get_configuration('v4_forward')
        values = values['internal_port'], values['external_port'], values['last_forward']
        return values
    else:  # version == 'v6'
        values = db_utils.get_configuration('v6_forward')
        values = values['internal_port'], values['external_port'], values['last_forward']
        return values


def get_internal_ip() -> Union[str, None]:
    """
    gets the internal nat ip of the machine
    :return: ip address | None if operation failed
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 8888))  # some address
        nat_ipv4 = s.getsockname()[0]
        s.close()
        return nat_ipv4
    except:
        return None


async def forward_port_upnp(devices, external_port: int, internal_port: int, protocol: str, nat_ip: str, lease_duration: int) -> bool:
    """
    attempt to forward a port using UPNP protocol
    note: if called again too shortly, a conflict exception will be raised
    :param devices: devices responded to ssdp discovery
    :param external_port: port accessible from outside the NAT
    :param internal_port: port accessible in this machine
    :param protocol: 'TCP' or 'UDP'
    :param nat_ip: this machine's ip in the NAT
    :param lease_duration: for how long should the router remember the mapping rule?
    :return: whatever the operation was successful.
    """

    success = False
    for d in devices:
        try:
            # get external ip before sending SOAP
            external_ip = d.WANIPConn1.GetExternalIPAddress()['NewExternalIPAddress']
            await db_utils.set_configuration('external_ip', external_ip)

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


def crc32c_sort_v4(peer_ip: str) -> int:
    """
    performs the crc32c sort operation for ipv4 as specified in BEP 40
    :param peer_ip: external ip address of the peer
    :return: priority of the peer's address
    """
    external_ip = db_utils.get_configuration('external_ip')
    octets = peer_ip.split('.')
    peer_ip = ''.join([bin(int(octet))[2:].zfill(8) for octet in octets])
    octets = external_ip.split('.')
    external_ip = ''.join([bin(int(octet))[2:].zfill(8) for octet in octets])

    for mask_length, bits in enumerate(zip(peer_ip, external_ip)):
        bit1, bit2 = bits
        if bit1 != bit2:
            break

    if mask_length < 16:
        mask = 4294923605  # FF.FF.55.55
    elif 16 <= mask_length < 24:
        mask = 4294967125  # FF.FF.FF.55
    else:
        mask = 4294967295  # FF.FF.FF.FF

    masked_peer_ip = int(peer_ip, 2) & mask
    masked_external_ip = int(external_ip, 2) & mask

    sorted_ip = sorted([masked_external_ip, masked_peer_ip])
    joined_ip = int(''.join([bin(ip)[2:].zfill(32) for ip in sorted_ip]), 2)
    priority = crc32c.crc32c(str(joined_ip).encode())
    return priority






