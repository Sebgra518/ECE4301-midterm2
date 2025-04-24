import cv2
import subprocess
import time
import socket
import struct
from picamera2 import Picamera2
import base64
import json


def main():

    # Set up the socket
    #UDP_IP = "172.20.10.2"  # Change to your PC's IP address
    UDP_IP = "192.168.254.82"  # Home Network
    UDP_PORT = 5005
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Initialize the camera
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (1280, 720)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.start()

    # Create the subprocess for Rust encryption
    proc = subprocess.Popen(
        ["./target/release/midterm2"],  # Path to the compiled Rust binary
        stdin=subprocess.PIPE,  # Pipe the input to Rust
        stdout=subprocess.PIPE,  # Capture the output of Rust (encrypted data)
        stderr=subprocess.PIPE
    )
    
    MAX_UDP_PACKET_SIZE = 64000  # Safe limit
    CHUNK_SIZE = MAX_UDP_PACKET_SIZE - 16  # Leave space for metadata

    print("Sending Data...")

    while True:
        # Capture frame
        frame = picam2.capture_array()
        

        # Encode frame to JPEG
        ret, frame_bytes = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        # Convert to bytes
        frame_data = frame_bytes.tobytes()

        length = struct.pack(">I", len(frame_data))
        proc.stdin.write(length + frame_data)


        start = time.perf_counter()
        proc.stdin.flush()

        line = proc.stdout.readline()
        output = json.loads(line)

        end = time.perf_counter()

        print(f"Took {end - start:.6f} seconds")

        with open("timings.txt", "a") as f:
            f.write(f"{end - start:.6f}\n")


        key = base64.b64decode(output["key"])
        iv = base64.b64decode(output["iv"])
        encrypted_frame = base64.b64decode(output["data"])

        frame_size = len(encrypted_frame)

        # Send Key
        sock.sendto(key, (UDP_IP, UDP_PORT))
        # Send IV
        sock.sendto(iv, (UDP_IP, UDP_PORT))

        # Send frame size as metadata (4 bytes)
        sock.sendto(struct.pack("!I", frame_size), (UDP_IP, UDP_PORT))

        # Send encrypted data in chunks
        for i in range(0, frame_size, CHUNK_SIZE):
            chunk = encrypted_frame[i:i + CHUNK_SIZE]
            sock.sendto(chunk, (UDP_IP, UDP_PORT))


if __name__ == "__main__":
    main()


#How to disable ARMv8 Gloally:
#1. cd /boot/cmdline.txt
#2. add: arm64.disable_aes=1