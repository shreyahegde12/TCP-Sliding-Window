"""
TCP Sliding Window Protocol - Server
CS 258 Project Assignment

Implements a TCP server that receives sequence numbers from a client,
tracks received and missing packets, sends cumulative ACKs, and
calculates goodput every 1000 received packets.

Authors: Vaibhav G, Shreya Hegde
"""

import socket

HOST = "0.0.0.0"
PORT = 5050
MAX_SEQ_NUM = 2 ** 16

VERBOSE = False
PROGRESS_INTERVAL = 100_000

# Data for report graphs
received_seq_log = []      # (time_index, received_seq_num)
receiver_window_log = []   # (time_index, receiver_window_size)

RECEIVER_WINDOW_SIZE = 1024


def send_line(conn, message):
    """Send a newline-terminated message over the TCP connection."""
    conn.sendall((message + "\n").encode())


def save_server_report_files():
    """Write CSV files for received sequence numbers and receiver window size."""
    with open("received_seq.csv", "w") as f:
        f.write("time,received_seq\n")
        for t, seq in received_seq_log:
            f.write(f"{t},{seq}\n")

    with open("receiver_window.csv", "w") as f:
        f.write("time,receiver_window\n")
        for t, w in receiver_window_log:
            f.write(f"{t},{w}\n")


def handle_client(conn, addr):
    """Handle one client session, then return to listening."""
    global received_seq_log, receiver_window_log

    client_ip, client_port = addr
    server_ip, server_port = conn.getsockname()
    print(f"Connected by {client_ip}:{client_port}")

    conn_file = conn.makefile("r")

    # Handshake
    hello = conn_file.readline().strip()
    print("Received handshake:", hello)

    if hello:
        send_line(conn, "SUCCESS")
        print("Sent: SUCCESS")
    else:
        print("No handshake received.")
        return

    print(f"\n===== SERVER STARTED =====")
    print(f"Sender   (Client) IP: {client_ip}:{client_port}")
    print(f"Receiver (Server) IP: {server_ip}:{server_port}")
    print(f"Max sequence number: {MAX_SEQ_NUM}")
    print("==========================\n")

    # Reset per-client session state
    received_seq_log = []
    receiver_window_log = []

    buffered_packets = set()
    missing_packets = set()
    expected_packet = 0
    received_count = 0
    sent_attempts_from_client = 0
    goodput_samples = []
    last_progress_mark = 0

    try:
        while True:
            line = conn_file.readline()
            if not line:
                print("Client disconnected.")
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split()

            if parts[0] == "SEQ" and len(parts) == 3:
                abs_id = int(parts[1])
                seq_num = int(parts[2])

                received_count += 1

                if abs_id in missing_packets:
                    missing_packets.discard(abs_id)

                if abs_id == expected_packet:
                    expected_packet += 1
                    while expected_packet in buffered_packets:
                        buffered_packets.discard(expected_packet)
                        expected_packet += 1
                elif abs_id > expected_packet:
                    buffered_packets.add(abs_id)
                    for pkt in range(expected_packet, abs_id):
                        if pkt not in buffered_packets:
                            missing_packets.add(pkt)

                ack_num = expected_packet % MAX_SEQ_NUM
                send_line(conn, f"ACK {expected_packet} {ack_num}")

                if received_count % 1000 == 0:
                    received_seq_log.append((received_count, seq_num))
                    receiver_window_log.append((received_count, RECEIVER_WINDOW_SIZE))

                if VERBOSE:
                    print(f"Received: abs={abs_id}, seq={seq_num}")
                    print(f"Sent: ACK abs={expected_packet}, seq={ack_num}")
                    print(f"Missing packets count: {len(missing_packets)}")

                if received_count - last_progress_mark >= PROGRESS_INTERVAL:
                    last_progress_mark = received_count
                    gp = goodput_samples[-1] if goodput_samples else 0
                    print(
                        f"[SERVER] Progress: received={received_count:,}, "
                        f"expected={expected_packet:,}, "
                        f"missing={len(missing_packets)}, goodput={gp:.4f}"
                    )

            elif parts[0] == "STATS" and len(parts) == 2:
                sent_attempts_from_client = int(parts[1])
                if sent_attempts_from_client > 0:
                    goodput = received_count / sent_attempts_from_client
                    goodput_samples.append(goodput)

            else:
                send_line(conn, "ERROR")
                print("Sent: ERROR")

    except (ConnectionResetError, BrokenPipeError):
        print("Client connection reset.")
    finally:
        print("\n===== SERVER SUMMARY =====")
        print(f"Sender   (Client) IP: {client_ip}:{client_port}")
        print(f"Receiver (Server) IP: {server_ip}:{server_port}")
        print(f"Total packets received: {received_count:,}")
        print(f"Total sent by client: {sent_attempts_from_client:,}")
        print(f"Current missing packets: {len(missing_packets)}")
        if goodput_samples:
            avg_goodput = sum(goodput_samples) / len(goodput_samples)
            print(f"Goodput samples collected: {len(goodput_samples)}")
            print(f"Average goodput (received/sent): {avg_goodput:.4f}")
        else:
            print("Average goodput: No samples collected yet")

        save_server_report_files()
        print("Server CSV files generated: received_seq.csv, receiver_window.csv")

        try:
            conn_file.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

        print("Waiting for next client...\n")


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print(f"Server listening on {HOST}:{PORT} ...")

    try:
        while True:
            conn, addr = server_socket.accept()
            handle_client(conn, addr)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    finally:
        server_socket.close()
        print("Server closed.")


if __name__ == "__main__":
    main()