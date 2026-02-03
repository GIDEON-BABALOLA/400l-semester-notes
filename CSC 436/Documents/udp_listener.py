"""
UDP Network Message Listener
Auto-starts with Windows, listens for incoming messages, and displays them in CMD
"""

import socket
import hashlib
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
UDP_IP = ""  # Listen on all interfaces
UDP_PORT = 5010
PASSWORD = "landmark"  # Change this to your desired password
LOG_DIR = Path(os.path.expandvars(r"%APPDATA%\NetMessages"))
QUEUE_FILE = LOG_DIR / "message_queue.json"

# Create log directory if it doesn't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

def calculate_password_hash(password):
    """Calculate SHA256 hash of password"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_queue():
    """Load message queue from file"""
    if QUEUE_FILE.exists():
        try:
            with open(QUEUE_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_queue(queue):
    """Save message queue to file"""
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)

def add_to_queue(message_data):
    """Add message to queue"""
    queue = load_queue()
    queue.append({
        "timestamp": datetime.now().isoformat(),
        "data": message_data
    })
    save_queue(queue)

def show_message_in_cmd(title, message, sender_ip):
    """Open new CMD window and display message"""
    cmd_content = f"""
@echo off
color 0A
title Network Message from {sender_ip}
cls
echo.
echo ========================================
echo NETWORK MESSAGE RECEIVED
echo ========================================
echo From: {sender_ip}
echo Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
echo ========================================
echo.
echo {message}
echo.
echo ========================================
pause
"""
    
    # Write to temp file
    temp_file = Path(os.path.expandvars(r"%TEMP%\net_msg_temp.bat"))
    with open(temp_file, 'w') as f:
        f.write(cmd_content)
    
    # Open new CMD window
    subprocess.Popen(f'cmd /k "{temp_file}"')

def handle_text_message(password_hash, message, sender_ip):
    """Handle incoming text message"""
    correct_hash = calculate_password_hash(PASSWORD)
    
    if password_hash != correct_hash:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] REJECTED - Invalid password from {sender_ip}")
        add_to_queue({"type": "rejected", "sender": sender_ip, "reason": "Invalid password"})
        return False
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] MESSAGE from {sender_ip}: {message}")
    show_message_in_cmd("Network Message", message, sender_ip)
    
    # Log to file
    log_file = LOG_DIR / f"messages_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(log_file, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] From {sender_ip}: {message}\n")
    
    return True

def listen():
    """Main listening loop"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((UDP_IP, UDP_PORT))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Listener started on port {UDP_PORT}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for messages...")
        
        while True:
            try:
                data, addr = sock.recvfrom(65507)
                message = data.decode('utf-8')
                parts = message.split("|", 2)  # Split into max 3 parts
                
                if len(parts) >= 3:
                    msg_type = parts[0]
                    password_hash = parts[1]
                    content = parts[2]
                    
                    if msg_type == "TEXT":
                        handle_text_message(password_hash, content, addr[0])
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Unknown message type: {msg_type}")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Invalid message format from {addr[0]}")
                    
            except Exception as e:
                print(f"[ERROR] {e}")
                
    except OSError as e:
        if e.errno == 48 or e.errno == 98:  # Port already in use
            print(f"[ERROR] Port {UDP_PORT} is already in use")
        else:
            print(f"[ERROR] {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    try:
        listen()
    except KeyboardInterrupt:
        print("\n[INFO] Listener stopped")
        sys.exit(0)
