import socket
import struct
import threading
import time

# Global variables
file_size = 0
tcp_connections = 0
udp_connections = 0
MAGIC_COOKIE = 0xabcddcba

def get_user_input():
    global file_size, tcp_connections, udp_connections
    file_size = int(input("Enter file size (bytes): "))
    tcp_connections = int(input("Enter number of TCP connections: "))
    udp_connections = int(input("Enter number of UDP connections: "))

def listen_for_broadcasts():
    # Set up a UDP socket to listen for broadcast messages
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.bind(('', 13117))

    while True:
        message, addr = udp_sock.recvfrom(1024)  # Receive message from server
        if len(message) >= 9 and is_valid_message(message):  # Ensure message is at least 9 bytes
            threading.Thread(target=process_offer_message, args=(message, addr)).start()

def is_valid_message(message):
    if len(message) < 4:
        return False
    magic_cookie = struct.unpack('!I', message[:4])[0]
    return magic_cookie == MAGIC_COOKIE

def process_offer_message(message, addr):
    # Extract server ports from the message (after the magic cookie and message type)
    server_udp_port = struct.unpack('!H', message[5:7])[0]
    server_tcp_port = struct.unpack('!H', message[7:9])[0]
    print(f"Server IP: {addr[0]}")
    print(f"Server UDP Port: {server_udp_port}")
    print(f"Server TCP Port: {server_tcp_port}")
    print("Received valid offer message from server.")
    
    # Create connections based on available connections
    create_connections(addr, server_tcp_port, server_udp_port)

def create_connections(addr, server_tcp_port, server_udp_port):
    threads = []
    global tcp_connections, udp_connections
    # Create one TCP connection
    if tcp_connections > 0:
        print("Creating TCP connection")
        tcp_connections -= 1
        thread = threading.Thread(target=tcp_transfer, args=(addr, server_tcp_port))
        threads.append(thread)
        thread.start()

    # Create one UDP connection
    if udp_connections > 0:
        print("Creating UDP connection")
        udp_connections -= 1
        thread = threading.Thread(target=udp_transfer, args=(addr, server_udp_port))
        threads.append(thread)
        thread.start()

def tcp_transfer(addr, server_tcp_port):
    try:
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
            tcp_sock.connect((addr[0], server_tcp_port))
            request_message = struct.pack('!I B Q', MAGIC_COOKIE, 0x03, file_size)
            tcp_sock.sendall(request_message)
            
            received_data = b""
            while len(received_data) < file_size:
                chunk = tcp_sock.recv(1024)  # Receive in 1 KB chunks (adjustable)
                if not chunk:
                    break
                received_data += chunk
            
            end_time = time.time()
            total_time = end_time - start_time
            speed = len(received_data) * 8 / total_time  # Calculate speed in bits/second
            print("--------------------------------------------")
            print("TCP Transfer - Completed")
            print(f"Time: {total_time:.2f} seconds")
            print(f"Speed: {speed:.2f} bits/second")
            print(f"Received data: {len(received_data)} bytes")
            print("--------------------------------------------")
        
        # Increase the TCP connection counter after the transfer finishes
        global tcp_connections
        tcp_connections += 1
        
    except Exception as e:
        print(f"Error during TCP transfer: {e}")


def udp_transfer(addr, server_udp_port):
    try:
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            request_message = struct.pack('!I B Q', MAGIC_COOKIE, 0x03, file_size)
            udp_sock.sendto(request_message, (addr[0], server_udp_port))

            received_segments = 0
            total_segments = 0
            while True:
                try:
                    udp_sock.settimeout(1)  # Timeout after 1 second if no packet is received
                    message, _ = udp_sock.recvfrom(1024)  # Receive message

                    if len(message) >= 21 and is_valid_message(message):  # Valid message check
                        total_segments = struct.unpack('!Q', message[5:13])[0] if total_segments == 0  else total_segments # Total number of segments
                        print(f"Received segment from server. {received_segments}/{total_segments}")
                        received_segments += 1

                    if received_segments == total_segments:
                        print(f"Received all {total_segments} segments.")
                        break  # Exit loop when all segments have been received
                except socket.timeout:
                    # If no data received for 1 second, consider the transfer complete
                    if received_segments == total_segments:
                        break

            end_time = time.time()
            total_time = end_time - start_time
            speed = received_segments * (1024 - 21) * 8 / total_time  # Calculate speed in bits/second
            packet_loss = (total_segments - received_segments) / total_segments * 100
            print("--------------------------------------------")
            print("UDP Transfer - Completed")
            print(f"Time: {total_time:.2f} seconds")
            print(f"Speed: {speed:.2f} bits/second")
            print(f"Packet Success Rate: {100 - packet_loss:.2f}%")
            print("--------------------------------------------")
        
        # Increase the UDP connection counter after the transfer finishes
        global udp_connections
        udp_connections += 1
                
    except Exception as e:
        print(f"Error during UDP transfer: {e}")



if __name__ == "__main__":
    get_user_input()
    listen_for_broadcasts()