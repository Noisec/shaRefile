
import http.server
import socketserver
import threading
import time
import os

PORT = 8080
f=open("host.txt","r") #example for host.txt: myhost.hopto.org
PUBLIC_IP = f.read()
f.close()
f2=open("path.txt","r") #example for path.txt: C:/public/myfiles/
LOCAL_FILES_PATH = f2.read()
f2.close()
REQUESTS_PER_SECOND = 1
TIMEOUT_SECONDS = 5

class ThrottledRequestHandler(http.server.SimpleHTTPRequestHandler):
    request_count = 0
    last_request_time = None
    clients = set()
    file_stats = {}

    def do_GET(self):
        # Check if request limit exceeded
        self.request_count += 1
        current_time = time.time()
        if self.last_request_time is not None and current_time - self.last_request_time < 1 / REQUESTS_PER_SECOND:
            self.send_error(429, "Too many requests")
            print("✘ Timeout by", self.client_address[0])
            return
        self.last_request_time = current_time

        # Remove port from URL
        url_parts = self.path.split(':')
        if len(url_parts) > 2:
            self.send_error(400, "Invalid URL")
            return
        if len(url_parts) == 2:
            if url_parts[1].startswith('/'):
                self.path = url_parts[1]
            else:
                self.send_error(400, "Invalid URL")
                return

        # Serve file
        file_path = LOCAL_FILES_PATH + self.path[1:]
        if not os.path.exists(file_path):
            self.send_error(404, "File not found")
            print("✘ Not existing file by", self.client_address[0])
            return
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())
        print("✓", self.client_address[0])

        # Log unique client IPs and file stats
        self.clients.add(self.client_address[0])
        if self.path[1:] in self.file_stats:
            self.file_stats[self.path[1:]] += 1
        else:
            self.file_stats[self.path[1:]] = 1

        # Write client IPs and file stats to files
        with open("clients.txt", "w") as f:
            f.write("\n".join(self.clients))
        with open("stats.txt", "w") as f:
            for file, count in self.file_stats.items():
                f.write(f"{file}:{count}\n")

with socketserver.ThreadingTCPServer(("", PORT), ThrottledRequestHandler) as httpd:
    print(f"Serving files from {LOCAL_FILES_PATH} at {PUBLIC_IP}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
