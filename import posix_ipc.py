import posix_ipc
import os
import time

# Create or open the named semaphore
sem = posix_ipc.Semaphore("/semaf", flags=posix_ipc.O_CREAT, initial_value=1)

# Open the underlying file to make it appear in /proc/<pid>/fd
fd = os.open("/dev/shm/sem.semaf", os.O_RDONLY)
print(f"Opened /dev/shm/sem.semaf as fd={fd}")
print(f"PID: {os.getpid()} — check /proc/{os.getpid()}/fd")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    os.close(fd)
    print("Closed fd.")
