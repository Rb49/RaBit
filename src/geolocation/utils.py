from geoip2 import database, errors
from math import radians, cos, sin, atan2, sqrt
from typing import Tuple, Union
import requests
from pathlib import Path
import json


__database_path = 'GeoLite2-City.mmdb'
__banned_json = 'banned_countries.json'


def get_banned_countries():
    # TODO move the function and json to a single config file
    with open(__abs_db_path(__banned_json), 'r') as json_file:
        banned_list = json.load(json_file)
        return banned_list


def __abs_db_path(file_name: str) -> Path:
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


def get_my_public_ip() -> Union[str, None]:
    """
    uses the ipify api to get my public ip, for geolocation calculations
    Note: blocking function!
    :return: ip address | None is failed
    """
    try:
        return requests.get('https://api.ipify.org', timeout=2).content.decode('utf8')
    except Exception as e:
        # print(e)
        return None


def calc_distance(ip_address1: str, ip_address2: str) -> Union[float, None]:
    """
    calculates the geolocation distance between two ip addresses
    :param ip_address1: ip_address
    :param ip_address2: ip_address
    :return: distance in km | None if failed
    """
    # check if addresses are in the database
    info1 = get_info(ip_address1)
    if info1 is None:
        return None
    info2 = get_info(ip_address2)
    if info2 is None:
        return None

    return __calc_haversine(info1[2], info1[3], info2[2], info2[3])


def get_info(ip_address: str) -> Union[Tuple[str, str, float, float], None]:
    """
    gets geolocation info about ip
    :param ip_address: ip_address
    :return: tuple: city, country, latitude, longitude | None if failed
    """
    with database.Reader(__abs_db_path(__database_path)) as reader:
        try:
            response = reader.city(ip_address)
            city = response.city.name
            country = response.country.name
            latitude = response.location.latitude
            longitude = response.location.longitude
            return city, country, latitude, longitude
        except errors.AddressNotFoundError:
            return None
