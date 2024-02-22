import time

# Measure 3 seconds
start_time = time.time()
while time.time() - start_time < 3:
    pass

print("3 seconds have passed.")
