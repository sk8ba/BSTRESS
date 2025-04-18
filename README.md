# 🔥 BSTRESS - Advanced Network Stress Testing Tool

**BSTRESS** is a high-performance Python-based network stress tester designed for **authorized penetration testing, security research, and network resilience validation**.

## ✨ Key Features
- **Multi-Vector Attacks**: HTTP Flood, SYN Flood (raw sockets), UDP Flood
- **Real-Time Monitoring**: Live stats, packet rates, and network usage
- **Optimized Performance**: Threaded architecture for maximum throughput
- **Professional Reporting**: Detailed analytics and error tracking
- **Ethical Focus**: Built-in legal warnings and confirmation prompts

## ⚠️ Legal Disclaimer
> **BSTRESS is for authorized security testing only.**  
> Unauthorized use against networks/systems you don't own is illegal.  
> By using this tool, you agree to adhere to all applicable laws.

## 🚀 Installation

git clone https://github.com/sk8ba/BSTRESS.git
cd bstress
pip install -r requirements.txt

## 🛠 Basic Usage

# Test with default settings (10 threads per attack)
python bstress.py TARGET_IP

# Aggressive test (50 threads per attack)
python bstress.py TARGET_IP -t 50

## 🌟 Use Cases
> Security Teams: Test firewall/DDoS protection
> Developers: Benchmark web server resilience
> Researchers: Study network protocol behavior
> Network Admins: Validate infrastructure limits
