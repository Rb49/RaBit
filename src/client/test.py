import os

# Open a file in binary read mode
with open('example.txt', 'rb') as file:
    # Get the file descriptor
    fd = file.fileno()

    # Seek to a specific index within the file (e.g., index 50)
    os.lseek(fd, 0, os.SEEK_SET)

    # Read up to 100 bytes from the file
    data = os.read(fd, 100)

    # Print the data
    print(data)
