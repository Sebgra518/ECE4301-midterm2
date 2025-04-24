import socket
import struct
import numpy as np
import cv2
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# Set up the socket
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Receiving started...")

buffer = b""
frame_size = None
iv = None
key = None

while True:
    try:

        data, addr = sock.recvfrom(64000)

        # If receiving Key (first 32 bytes)
        if len(data) == 32:
            key = data
            buffer = b""  # Reset buffer
            frame_size = None  # Reset frame size
            continue

        # If receiving IV (first 16 bytes)
        if len(data) == 16:
            iv = data
            buffer = b""  # Reset buffer
            frame_size = None  # Reset frame size
            continue

        # If receiving frame size (4 bytes)
        if len(data) == 4:
            frame_size = struct.unpack("!I", data)[0]
            buffer = b""  # Reset buffer
            continue

        buffer += data  # Append chunk to buffer

        # Wait until full frame is received
        if frame_size and len(buffer) >= frame_size:

            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_data = unpad(cipher.decrypt(buffer[:frame_size]), AES.block_size)

            eoi_index = decrypted_data.find(b'\xFF\xD9')
            if eoi_index != -1:
                jpeg_data = decrypted_data[:eoi_index + 2]

                # Decode and display frame
                img_array = np.frombuffer(jpeg_data, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                if frame is not None:
                    cv2.imshow("Received Frame", frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # Reset buffer after successful frame decoding
            buffer = b""
            frame_size = None

    except Exception as e:
        print(f"Decryption error: {e}")
        buffer = b""  # Clear buffer on error
        frame_size = None

# Cleanup
sock.close()
cv2.destroyAllWindows()
