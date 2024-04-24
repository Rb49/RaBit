import src.app_data.db_utils as db_utils

from geoip2 import database, errors
from math import radians, cos, sin, atan2, sqrt
from typing import Tuple, Union
import requests
from pathlib import Path


__database_path = 'GeoLite2-City.mmdb'


def abs_db_path(file_name: str) -> Path:
    """
    computes the absolute path of the file (based on this root dir)
    :return: absolute path
    """
    hpath_parent = Path(__file__).parent
    return hpath_parent.joinpath(file_name)

    # thanks to sapoj for help with this function


def __calc_haversine(lat1: float, long1: float, lat2: float, long2: float) -> float:
    """
    calculate the haversine function for two coords
    :return: distances in km
    """
    R = 6371  # earths radius
    lat1, long1, lat2, long2 = list(map(radians, [lat1, long1, lat2, long2]))

    dlat = lat2 - lat1
    dlong = long2 - long1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlong / 2) ** 2
    c = atan2(sqrt(a), sqrt(1 - a))
    d = 2 * R * c

    return d


async def get_my_public_ip() -> Union[str, None]:
    """
    gets external_ip from the router
    backup: uses the ipify api to get my public ip, for geolocation calculations
    note: blocking function!
    :return: ip address | None is failed
    """
    external_ip = db_utils.get_configuration('external_ip')
    if not external_ip:
        # backup
        try:
            external_ip = requests.get('https://api.ipify.org', timeout=2).content.decode('utf8')
            await db_utils.set_configuration('external_ip', external_ip)
            return external_ip
        except:
            return None
    return external_ip


def calc_distance(ip_address1: str, ip_address2: str) -> Union[float, None]:
    """
    calculates the geolocation distance between two ip addresses
    :param ip_address1: ip_address
    :param ip_address2: ip_address
    :return: distance in km | None if failed
    """
    # check if addresses are in the database
    info1: Tuple = get_info(ip_address1)
    info2: Tuple = get_info(ip_address2)
    if None in [info1, info2]:
        return None

    return __calc_haversine(info1[2], info1[3], info2[2], info2[3])


def get_info(ip_address: str) -> Union[Tuple[str, str, float, float], None]:
    """
    gets geolocation info about ip
    :param ip_address: ip_address
    :return: tuple: city, country code, latitude, longitude | None if failed
    """
    with database.Reader(abs_db_path(__database_path)) as reader:
        try:
            response = reader.city(ip_address)
            city = response.city.name
            country = response.country.iso_code
            latitude = response.location.latitude
            longitude = response.location.longitude
            return city, country, latitude, longitude
        except errors.AddressNotFoundError:
            return None
