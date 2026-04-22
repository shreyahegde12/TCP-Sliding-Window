"""
TCP Sliding Window Protocol - Client
CS 258 Project Assignment

Implements a TCP client that sends packets to a server using the sliding
window protocol. The client probabilistically drops 1% of packets and
retransmits them after every RETX_INTERVAL sequence numbers.

Authors: Vaibhav G, Shreya Hegde
"""

import socket
import random

SERVER_IP = "172.20.10.14"  # change this to the server's IP address
PORT = 5050

TOTAL_PACKETS = 10_000_000
WINDOW_SIZE = 1024
DROP_PROBABILITY = 0.01
RETX_INTERVAL = 100
GOODPUT_INTERVAL = 1000
MAX_SEQ_NUM = 2 ** 16

VERBOSE = False
PROGRESS_INTERVAL = 100_000

# Data for report graphs/table
sender_window_log = []         # (time_index, sender_window_size)
drop_log = []                  # (time_index, dropped_seq_num)
retransmission_counts = {}     # abs_id -> number of retransmissions


def send_line(sock, message):
    """Send a newline-terminated message over the TCP socket."""
    sock.sendall((message + "\n").encode())


def save_client_report_files():
    """Write CSV files for sender window, drops, and retransmission table."""
    with open("sender_window.csv", "w") as f:
        f.write("time,sender_window\n")
        for t, w in sender_window_log:
            f.write(f"{t},{w}\n")

    with open("drops.csv", "w") as f:
        f.write("time,dropped_seq\n")
        for t, seq in drop_log:
            f.write(f"{t},{seq}\n")

    table = {1: 0, 2: 0, 3: 0, 4: 0}
    for count in retransmission_counts.values():
        if count in table:
            table[count] += 1

    with open("retransmissions.csv", "w") as f:
        f.write("retransmissions,packet_count\n")
        for k in [1, 2, 3, 4]:
            f.write(f"{k},{table[k]}\n")


def retransmit_dropped(sock, dropped_packets, sent_attempts):
    if VERBOSE and dropped_packets:
        print(f"\n--- RETRANSMITTING {len(dropped_packets)} DROPPED PACKETS ---")

    remaining = []

    for abs_id in sorted(dropped_packets):
        seq_num = abs_id % MAX_SEQ_NUM
        msg = f"SEQ {abs_id} {seq_num}"

        retransmission_counts[abs_id] = retransmission_counts.get(abs_id, 0) + 1

        try:
            if random.random() < DROP_PROBABILITY:
                if VERBOSE:
                    print(f"RE-DROPPED: abs={abs_id}, seq={seq_num}")
                remaining.append(abs_id)
                drop_log.append((abs_id, seq_num))
            else:
                if VERBOSE:
                    print(f"Retransmitting: abs={abs_id}, seq={seq_num}")
                send_line(sock, msg)

            sent_attempts += 1

        except (BrokenPipeError, ConnectionResetError, OSError):
            print("Server connection lost during retransmission.")
            return remaining + dropped_packets[dropped_packets.index(abs_id) + 1:], sent_attempts, False

    if VERBOSE and dropped_packets:
        print("--------------------------------------\n")

    return remaining, sent_attempts, True


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((SERVER_IP, PORT))
    except OSError as e:
        print(f"Could not connect to server: {e}")
        return

    client_file = client_socket.makefile("r")
    local_ip, local_port = client_socket.getsockname()

    dropped_packets = []
    sent_attempts = 0
    base = 0
    next_seq = 0
    last_ack = -1
    duplicate_ack_count = 0
    goodput_samples = []
    last_progress_mark = 0

    try:
        send_line(client_socket, "network")
        response = client_file.readline().strip()
        print("Server says:", response)

        if response != "SUCCESS":
            print("Handshake failed.")
            return

        print("\n===== CLIENT STARTED =====")
        print(f"Sender   (Client) IP: {local_ip}:{local_port}")
        print(f"Receiver (Server) IP: {SERVER_IP}:{PORT}")
        print(f"Total packets: {TOTAL_PACKETS:,}")
        print(f"Window size: {WINDOW_SIZE}")
        print(f"Max sequence number: {MAX_SEQ_NUM}")
        print(f"Drop probability: {DROP_PROBABILITY}")
        print("==========================\n")

        running = True

        while base < TOTAL_PACKETS and running:
            while next_seq < base + WINDOW_SIZE and next_seq < TOTAL_PACKETS:
                abs_id = next_seq
                seq_num = abs_id % MAX_SEQ_NUM
                msg = f"SEQ {abs_id} {seq_num}"

                try:
                    if random.random() < DROP_PROBABILITY:
                        if VERBOSE:
                            print(f"DROPPED: abs={abs_id}, seq={seq_num}")
                        if abs_id not in dropped_packets:
                            dropped_packets.append(abs_id)
                        drop_log.append((abs_id, seq_num))
                    else:
                        if VERBOSE:
                            print(f"Sending: abs={abs_id}, seq={seq_num}")
                        send_line(client_socket, msg)

                    sent_attempts += 1
                    next_seq += 1

                except (BrokenPipeError, ConnectionResetError, OSError):
                    print("Server stopped while client was running.")
                    running = False
                    break

                if next_seq % 1000 == 0:
                    sender_window_log.append((next_seq, WINDOW_SIZE))

                if next_seq % RETX_INTERVAL == 0 and dropped_packets:
                    dropped_packets, sent_attempts, ok = retransmit_dropped(
                        client_socket,
                        dropped_packets,
                        sent_attempts
                    )
                    if not ok:
                        running = False
                        break

                if next_seq % GOODPUT_INTERVAL == 0:
                    try:
                        send_line(client_socket, f"STATS {sent_attempts}")
                        current_goodput = next_seq / sent_attempts if sent_attempts > 0 else 0
                        goodput_samples.append(current_goodput)
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        print("Server stopped while sending stats.")
                        running = False
                        break

                if next_seq - last_progress_mark >= PROGRESS_INTERVAL:
                    last_progress_mark = next_seq
                    current_goodput = next_seq / sent_attempts if sent_attempts > 0 else 0
                    print(
                        f"[CLIENT] Progress: sent_original={next_seq:,}, "
                        f"sent_attempts={sent_attempts:,}, acked={base:,}, "
                        f"pending_drops={len(dropped_packets)}, goodput={current_goodput:.4f}"
                    )

            if not running:
                break

            try:
                ack_line = client_file.readline()
            except (ConnectionResetError, OSError):
                print("Server stopped while client was waiting for ACK.")
                break

            if not ack_line:
                print("Server closed connection.")
                break

            ack_line = ack_line.strip()
            parts = ack_line.split()

            if len(parts) == 3 and parts[0] == "ACK":
                ack_abs = int(parts[1])
                ack_seq = int(parts[2])

                if ack_abs == last_ack:
                    duplicate_ack_count += 1
                else:
                    duplicate_ack_count = 0

                last_ack = ack_abs
                base = ack_abs

                if VERBOSE:
                    print(f"Received: ACK abs={ack_abs}, seq={ack_seq}")
                    print(f"Window: [{base}, {base + WINDOW_SIZE - 1}], next_seq={next_seq}")
            else:
                print("Invalid ACK received:", ack_line)
                break

            if dropped_packets and (duplicate_ack_count >= 3 or base < next_seq):
                if VERBOSE:
                    print("\nRetransmitting due to stall...\n")
                dropped_packets, sent_attempts, ok = retransmit_dropped(
                    client_socket,
                    dropped_packets,
                    sent_attempts
                )
                if not ok:
                    break
                duplicate_ack_count = 0

    finally:
        try:
            send_line(client_socket, f"STATS {sent_attempts}")
        except Exception:
            pass

        try:
            client_file.close()
        except Exception:
            pass
        try:
            client_socket.close()
        except Exception:
            pass

        final_goodput = TOTAL_PACKETS / sent_attempts if sent_attempts > 0 else 0

        print("\n===== CLIENT SUMMARY =====")
        print(f"Sender   (Client) IP: {local_ip}:{local_port}")
        print(f"Receiver (Server) IP: {SERVER_IP}:{PORT}")
        print(f"Total original packets: {TOTAL_PACKETS:,}")
        print(f"Total sent attempts: {sent_attempts:,}")
        print(f"Final goodput: {final_goodput:.4f}")

        if goodput_samples:
            avg_goodput = sum(goodput_samples) / len(goodput_samples)
            print(f"Average periodic goodput: {avg_goodput:.4f}")
        else:
            print("Average periodic goodput: No samples collected yet")

        print("\nRetransmission Table:")
        table = {1: 0, 2: 0, 3: 0, 4: 0}
        for count in retransmission_counts.values():
            if count in table:
                table[count] += 1
        print(f"  {'# Retransmissions':<20} {'# Packets':<10}")
        for k in [1, 2, 3, 4]:
            print(f"  {k:<20} {table[k]:<10}")

        save_client_report_files()
        print("\nClient CSV files generated: sender_window.csv, drops.csv, retransmissions.csv")


if __name__ == "__main__":
    main()