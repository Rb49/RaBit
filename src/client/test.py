import socket

host = "example.com"
port = 80

result = socket.getaddrinfo(host, port)
addresses = [res[4][0:2] for res in result]
print(addresses)

