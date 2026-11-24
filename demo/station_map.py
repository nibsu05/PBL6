"""Local viewer for the verified short-range replay. Run from the repo root."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).with_name('station_map')
SNAPSHOT = ROOT / 'data' / 'operational' / 'gfs_short_range_closeout_2026_11_24' / 'station_map_private.json'
ROUTES = {
    '/': (STATIC / 'index.html', 'text/html; charset=utf-8'),
    '/map.css': (STATIC / 'map.css', 'text/css; charset=utf-8'),
    '/map.js': (STATIC / 'map.js', 'application/javascript; charset=utf-8'),
    '/api/short-range': (SNAPSHOT, 'application/json; charset=utf-8'),
}


class MapHandler(BaseHTTPRequestHandler):
    def respond(self, status, body, media_type):
        self.send_response(status)
        self.send_header('Content-Type', media_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com; "
            "img-src 'self' data: https://unpkg.com https://tile.openstreetmap.org; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Keep the local station export available only to this viewer. No
        # directory listing, dynamic filesystem path or cross-origin access.
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}' or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.respond(403, b'Local access only', 'text/plain; charset=utf-8')
            return
        route = ROUTES.get(urlsplit(self.path).path)
        if route is None:
            self.respond(404, b'Not found', 'text/plain; charset=utf-8')
            return
        path, media_type = route
        try:
            body = path.read_bytes()
        except OSError:
            self.respond(503, b'{"error":"snapshot_unavailable"}', 'application/json; charset=utf-8')
            return
        self.respond(200, body, media_type)


def main():
    parser = argparse.ArgumentParser(description='Xem dự báo mưa tại trạm trên máy này.')
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    with ThreadingHTTPServer(('127.0.0.1', args.port), MapHandler) as server:
        print(f'http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
