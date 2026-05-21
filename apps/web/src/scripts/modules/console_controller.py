import sys
import json
import os
from typing import Dict, Optional
import asyncio
import paramiko
import socket
import time
from datetime import datetime
import traceback
import uuid

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "src/data/accounts.json")
DEVICES_FILE = os.path.join(BASE_DIR, "src/data/devices.json")
TUNNEL_STATUS_FILE = os.path.join(BASE_DIR, "src/data/tunnel_status.json")
ACTIVE_SESSIONS_FILE = os.path.join(BASE_DIR, "src/data/active_sessions.json")

# In-memory storage for SSH connections
active_connections: Dict[str, paramiko.SSHClient] = {}

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_devices():
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def check_tunnel():
    if os.path.exists(TUNNEL_STATUS_FILE):
        try:
            with open(TUNNEL_STATUS_FILE, "r", encoding="utf-8") as f:
                tunnel_data = json.load(f)
                if tunnel_data.get("status") == "CONNECTED":
                    return tunnel_data
        except:
            pass
    return None

def create_ssh_connection(device, account, tunnel_config=None):
    """Create SSH connection to device"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Configure timeouts and compression
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # Socket timeout
        
        # Connection parameters
        connect_kwargs = {
            'hostname': device['address'],
            'port': 22,
            'username': account['username'],
            'password': account['password'],
            'timeout': 10,  # Connection timeout
            'banner_timeout': 8,  # SSH banner timeout
            'compress': True,  # Enable compression
            'sock': sock
        }
        
        # If tunnel is active, connect through it
        if tunnel_config:
            proxy_command = f"nc -X connect -x {tunnel_config['socks_host']}:{tunnel_config['socks_port']} {device['address']} 22"
            connect_kwargs['sock'] = paramiko.ProxyCommand(proxy_command)
        
        ssh.connect(**connect_kwargs)
        
        # Test connection with a simple command
        stdin, stdout, stderr = ssh.exec_command('echo "SSH connection established"', timeout=5)
        stdout.read()
        
        return ssh
        
    except Exception as e:
        if 'ssh' in locals():
            ssh.close()
        raise e

def execute_command_on_device(device_id, command):
    """Execute command on device via SSH"""
    try:
        # Load device data
        devices = load_devices()
        device = next((d for d in devices if d['id'] == device_id), None)
        
        # Debug logging
        print(f"[DEBUG] Looking for device_id: {device_id}", file=sys.stderr)
        print(f"[DEBUG] Total devices loaded: {len(devices)}", file=sys.stderr)
        if devices and len(devices) > 0:
            print(f"[DEBUG] First device ID example: {devices[0].get('id', 'NO_ID')}", file=sys.stderr)
        
        if not device:
            return {"success": False, "error": f"Device not found. Searched for ID: {device_id}"}
        
        print(f"[DEBUG] Found device: {device.get('hostname', 'NO_HOSTNAME')}", file=sys.stderr)
        
        if device.get('status') != 'SYNCED':
            return {"success": False, "error": f"Device not synchronized. Status: {device.get('status')}"}
        
        # Load account data
        accounts = load_accounts()
        account = next((a for a in accounts if a['id'] == device['account_id']), None)
        
        if not account:
            return {"success": False, "error": "Account not found"}
        
        # Check if tunnel is needed
        tunnel_config = check_tunnel()
        
        # Create SSH connection
        ssh = create_ssh_connection(device, account, tunnel_config)
        
        # Execute command
        stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
        
        # Read output
        output_lines = []
        error_lines = []
        
        for line in stdout:
            output_lines.append(line.rstrip('\n'))
        
        for line in stderr:
            error_lines.append(line.rstrip('\n'))
        
        ssh.close()
        
        # Prepare response
        output_text = '\n'.join(output_lines) if output_lines else ''
        error_text = '\n'.join(error_lines) if error_lines else ''
        
        if error_text and not output_text:
            return {"success": False, "error": error_text}
        
        result_text = output_text
        if error_text:
            result_text += f"\n[STDERR]: {error_text}"
        
        return {"success": True, "output": result_text}
        
    except Exception as e:
        return {"success": False, "error": f"SSH Error: {str(e)}"}

def create_session(device_id, hostname, address):
    """Create new SSH session"""
    try:
        session_id = str(uuid.uuid4())
        
        # For now, we'll simulate session creation
        # In a real implementation, you might want to keep persistent connections
        
        return {
            "success": True,
            "session_id": session_id,
            "device_name": hostname,
            "device_address": address,
            "initial_output": f"Session created for {hostname} ({address})\nReady to accept commands..."
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_session(session_id):
    """Delete SSH session"""
    try:
        # Close any active connections for this session
        if session_id in active_connections:
            active_connections[session_id].close()
            del active_connections[session_id]
        
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_sessions():
    """Get all active sessions"""
    try:
        # For now, return empty list
        # In a real implementation, you'd track active sessions
        return {"success": True, "sessions": []}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Invalid arguments"}))
        return

    method = sys.argv[1]
    
    try:
        if method == "execute_command":
            payload = json.loads(sys.argv[2])
            device_id = payload.get('deviceId')
            command = payload.get('command')
            
            # Debug logging
            print(f"[DEBUG] Method: execute_command", file=sys.stderr)
            print(f"[DEBUG] Payload: {payload}", file=sys.stderr)
            print(f"[DEBUG] Device ID: {device_id}", file=sys.stderr)
            print(f"[DEBUG] Command: {command}", file=sys.stderr)
            
            if not device_id or not command:
                print(json.dumps({"success": False, "error": "Missing deviceId or command"}))
                return
            
            result = execute_command_on_device(device_id, command)
            print(json.dumps(result))
            
        elif method == "create_session":
            payload = json.loads(sys.argv[2])
            device_id = payload.get('device_id')
            hostname = payload.get('hostname')
            address = payload.get('address')
            
            result = create_session(device_id, hostname, address)
            print(json.dumps(result))
            
        elif method == "delete_session":
            payload = json.loads(sys.argv[2])
            session_id = payload.get('session_id')
            
            result = delete_session(session_id)
            print(json.dumps(result))
            
        elif method == "get_sessions":
            result = get_sessions()
            print(json.dumps(result))
            
        else:
            print(json.dumps({"success": False, "error": "Unknown method"}))
            
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    main()