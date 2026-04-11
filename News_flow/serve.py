"""
QuantLab News Flow -- Local Server
Serves the News_flow directory on http://localhost:8765

Run once, leave it running. Open in VSCode Simple Browser:
  http://localhost:8765/today

Usage:
  python C:/QuantLab/Data_Lab/News_flow/serve.py
"""

import http.server
import socketserver
import webbrowser
import os
from datetime import date
from pathlib import Path

PORT = 8765
DIR  = Path(__file__).parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)

    def do_GET(self):
        # /today → redirect to today's dashboard
        if self.path in ('/', '/today', '/today/'):
            today = date.today().isoformat()
            self.send_response(302)
            self.send_header('Location', f'/{today}.html')
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, format, *args):
        pass  # suppress per-request noise


if __name__ == '__main__':
    os.chdir(DIR)
    print(f'\n-- News Flow Server ------------------------------------')
    print(f'   Serving: {DIR}')
    print(f'   URL:     http://localhost:{PORT}/today')
    print(f'   Stop:    Ctrl+C')
    print(f'-------------------------------------------------------\n')

    try:
        httpd = socketserver.TCPServer(('', PORT), Handler)
        httpd.allow_reuse_address = True
    except OSError:
        print(f'Port {PORT} already in use — server already running. Nothing to do.')
        raise SystemExit(0)

    with httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nServer stopped.')
