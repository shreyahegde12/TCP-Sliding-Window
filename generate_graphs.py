"""
Graph and Table Generator for TCP Sliding Window Protocol
CS 258 Project Assignment

Reads CSV files produced by server2.py and client2.py, then generates:
  1. Combined Sender & Receiver window size over time 
  2. TCP Sequence number received over time 
  3. TCP Sequence number dropped over time 
  4. Retransmission table 

Authors: Vaibhav G, Shreya Hegde 
"""

import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_csv(filename):
    """Read a two-column CSV (header + int data) and return two lists."""
    col1, col2 = [], []
    with open(filename) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            col1.append(int(row[0]))
            col2.append(int(row[1]))
    return col1, col2


def main():
    # ---- Graph 1: TCP Sender and Receiver Window Size over Time ----
    fig, ax = plt.subplots(figsize=(10, 5))
    sx, sy = read_csv("sender_window.csv")
    rx, ry = read_csv("receiver_window.csv")
    ax.plot(sx, sy, label="Sender Window Size", linewidth=1.2)
    ax.plot(rx, ry, label="Receiver Window Size", linewidth=1.2, linestyle="--")
    ax.set_title("TCP Sender and Receiver Window Size over Time")
    ax.set_xlabel("Time (Packet Index)")
    ax.set_ylabel("Window Size")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig("window_sizes.png", dpi=150)
    plt.close(fig)

    # ---- Graph 2: TCP Sequence Number Received over Time ----
    fig, ax = plt.subplots(figsize=(10, 5))
    t, seq = read_csv("received_seq.csv")
    ax.plot(t, seq, linewidth=0.8)
    ax.set_title("TCP Sequence Number Received over Time")
    ax.set_xlabel("Time (Packets Received)")
    ax.set_ylabel("Sequence Number (mod 2^16)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig("received_seq.png", dpi=150)
    plt.close(fig)

    # ---- Graph 3: TCP Sequence Number Dropped over Time ----
    fig, ax = plt.subplots(figsize=(10, 5))
    dt, ds = read_csv("drops.csv")
    ax.scatter(dt, ds, s=3, alpha=0.5)
    ax.set_title("TCP Sequence Number Dropped over Time")
    ax.set_xlabel("Time (Packet Index)")
    ax.set_ylabel("Dropped Sequence Number (mod 2^16)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig("drops.png", dpi=150)
    plt.close(fig)

    # ---- Table: Retransmissions ----
    retx = {}
    with open("retransmissions.csv") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            retx[int(row[0])] = int(row[1])

    print("\n========== Retransmission Table ==========")
    print(f"  {'# of Retransmissions':<25} {'# of Packets':<15}")
    print(f"  {'-'*25} {'-'*15}")
    for k in [1, 2, 3, 4]:
        print(f"  {k:<25} {retx.get(k, 0):<15}")
    print("==========================================\n")

    print("Graphs generated:")
    print("  - window_sizes.png   (Sender & Receiver window size)")
    print("  - received_seq.png   (Sequence number received)")
    print("  - drops.png          (Sequence number dropped)")


if __name__ == "__main__":
    main()