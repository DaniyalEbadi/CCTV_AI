#!/usr/bin/env python3
"""
Simple HTTP server to serve the AI detection dashboard.
"""
import http.server
import socketserver
import os
import sys
import subprocess
import signal
import time
from pathlib import Path


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def end_headers(self):
        # Add CORS headers to allow API requests from the dashboard
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()


def kill_process_on_port(port):
    """Kill any process running on the specified port."""
    try:
        # Find the process ID using the port
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        
        pid = None
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[4]
                    break
        
        if pid:
            print(f"Killing process {pid} running on port {port}...")
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"Process on port {port} has been stopped.")
            except OSError:
                # Process might already be gone
                print(f"Process {pid} was already terminated.")
    except subprocess.CalledProcessError:
        print(f"Could not find processes using netstat.")
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")


def is_port_available(port):
    """Check if a port is available."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('127.0.0.1', port))
        return result != 0


def start_server(port=8081):  # Changed to port 8081 to avoid conflicts
    """Start the HTTP server to serve the dashboard."""
    print(f"Starting server on http://localhost:{port}")
    print(f"Open your browser to http://localhost:{port}/detection_dashboard.html to view the dashboard")
    
    # Kill any existing process on the port
    kill_process_on_port(port)
    
    # Wait for port to become available
    print("Waiting for port to become available...")
    timeout = 10  # Wait up to 10 seconds
    while not is_port_available(port) and timeout > 0:
        time.sleep(0.5)
        timeout -= 0.5
    
    if not is_port_available(port):
        print(f"Port {port} is still not available. Please wait a moment and try again.")
        return
    
    handler = DashboardHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Server running at http://localhost:{port}/")
            print("Press Ctrl+C to stop the server")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 10048:  # Address already in use
            print(f"Port {port} is still in use. Please wait a moment and try again.")
        else:
            raise


if __name__ == "__main__":
    port = 8081  # Changed to port 8081 to avoid conflicts
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number. Using default port 8081.")
    
    start_server(port)