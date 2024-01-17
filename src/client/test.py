import socket


def udp():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 0))

    _, port = udp_socket.getsockname()

    try:
        while True:
            data, address = udp_socket.recvfrom(1024)
            print(f"{address}: {data.decode('utf-8')}")

    except Exception as e:
        print(e)
    finally:
        udp_socket.close()


if __name__ == "__main__":
    udp()
