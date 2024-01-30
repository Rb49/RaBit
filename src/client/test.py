import bitstring
import requests

s = requests.get('https://api.ipify.org', timeout=2).content.decode('utf8')
print(s)