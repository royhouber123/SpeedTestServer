import socket
import struct
import threading
import time
import os

MAGIC_COOKIE = 0xabcddcba
BUFFER_SIZE = 1024  
PAYLOAD_SIZE = BUFFER_SIZE - 21
BROADCAST_PORT = 13117
UDP_PORT = 8080
TCP_PORT = 9090

# Utility function to get the server's IP address
def get_server_ip():
    """Get the server's local IP address."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  # Connect to an external host; no data sent
            return s.getsockname()[0]
        except Exception as e:
            print(f"Failed to determine local IP: {e}")
            return "127.0.0.1"  # Fallback to localhost if no IP is found

def send_broadcast_messages():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    server_ip = get_server_ip()
    message = struct.pack('!I B H H', MAGIC_COOKIE, 0x02, UDP_PORT, TCP_PORT)

    while True:
        udp_sock.sendto(message, ('<broadcast>', BROADCAST_PORT))
        print(f"Broadcast message sent from {server_ip}")
        time.sleep(10)

def handle_tcp_connections(client_sock, client_addr):
    try:
        request_message = client_sock.recv(1024)
        if not is_valid_request_message(request_message):
            print(f"Invalid request message from {client_addr}.")
            return

        file_size = struct.unpack('!Q', request_message[5:13])[0]
        total_segments = (file_size + PAYLOAD_SIZE - 1) // PAYLOAD_SIZE

        for current_segment in range(1, total_segments + 1):
            magic_cookie = struct.pack('!I', 0xabcddcba)
            message_type = struct.pack('!B', 0x04)
            total_segments_packed = struct.pack('!Q', total_segments)
            current_segment_packed = struct.pack('!Q', current_segment)
            payload = os.urandom(PAYLOAD_SIZE)

            payload_message = (
                magic_cookie
                + message_type
                + total_segments_packed
                + current_segment_packed
                + payload
            )
            try:
                client_sock.sendall(payload_message)
                #print(f"Sent segment {current_segment}/{total_segments} to {client_addr} - TCP connection.")
            except BrokenPipeError:
                print(f"Broken pipe error while sending segment {current_segment}/{total_segments} to {client_addr}.")
                break
            
    except Exception as e:
        print(f"Error handling TCP connection with {client_addr}: {e}")
    finally:
        print(f"Closing TCP connection with {client_addr}.")
        client_sock.close()

def handle_udp_connections():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((get_server_ip(), UDP_PORT))
    print(f"UDP server listening on port {UDP_PORT}.")

    while True:
        try:
            request_message, client_addr = udp_sock.recvfrom(1024)
            if not is_valid_request_message(request_message):
                print(f"Invalid request message from {client_addr}.")
                continue

            file_size = struct.unpack('!Q', request_message[5:13])[0]
            total_segments = (file_size + PAYLOAD_SIZE - 1) // PAYLOAD_SIZE

            for current_segment in range(1, total_segments + 1):
                magic_cookie = struct.pack('!I', 0xabcddcba)
                message_type = struct.pack('!B', 0x04)
                total_segments_packed = struct.pack('!Q', total_segments)
                current_segment_packed = struct.pack('!Q', current_segment)
                payload = os.urandom(PAYLOAD_SIZE)

                payload_message = (
                    magic_cookie
                    + message_type
                    + total_segments_packed
                    + current_segment_packed
                    + payload
                )
                udp_sock.sendto(payload_message, client_addr)
                print(f"Sent segment {current_segment}/{total_segments} to {client_addr} - UDP connection.")

        except Exception as e:
            print(f"Error handling UDP connection: {e}")

def is_valid_request_message(message):
    if len(message) < 13:
        return False

    magic_cookie = struct.unpack('!I', message[:4])[0]
    return magic_cookie == MAGIC_COOKIE

def run_server():
    server_ip = get_server_ip()
    print(f"Server started, listening on {server_ip}")

    threading.Thread(target=send_broadcast_messages).start()
    threading.Thread(target=handle_udp_connections).start()

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.bind((server_ip, TCP_PORT))
    tcp_sock.listen(5)
    print(f"TCP server listening on port {TCP_PORT}.")

    while True:
        client_sock, client_addr = tcp_sock.accept()
        threading.Thread(target=handle_tcp_connections, args=(client_sock, client_addr)).start()

if __name__ == "__main__":
    run_server()