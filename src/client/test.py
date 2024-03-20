def count_different_bytes(file1_path, file2_path):
    with open(file1_path, 'rb') as file1, open(file2_path, 'rb') as file2:
        bytes1 = file1.read()
        bytes2 = file2.read()

    if len(bytes1) != len(bytes2):
        raise ValueError("Files are not of the same size")
    print(len(bytes1), len(bytes2))
    count = sum(1 for b1, b2 in zip(bytes1, bytes2) if b1 != b2)
    return count

file1_path = r"C:\Users\roeyb\Downloads\debian-edu-12.4.0-amd64-netinst.iso"
file2_path = r"C:\Users\roeyb\OneDrive\Documents\GitHub\RaBit\RaBit\results\debian-edu-12.4.0-amd64-netinst.iso"

try:
    different_bytes_count = count_different_bytes(file1_path, file2_path)
    print(f"Number of different bytes between {file1_path} and {file2_path}: {different_bytes_count}")
except FileNotFoundError:
    print("One or both files not found.")
except ValueError as e:
    print(e)
