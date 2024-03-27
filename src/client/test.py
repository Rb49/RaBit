import threading

# Define a shared condition variable
condition = threading.Condition()

# This is the function that the second thread will run
def second_thread():
    with condition:
        # Wait until the condition is notified
        condition.wait()
        # Do something after being notified
        print("Second thread started")

# Create and start the second thread
t = threading.Thread(target=second_thread)
t.start()

# This is the first thread that will signal the second thread to start
with condition:
    # Do some work
    # Signal the second thread to start
    condition.notify()
