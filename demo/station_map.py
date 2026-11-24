"""Loopback-only rainfall app with a private account and forecast verification."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.station_map_accounts import AccountExists, Accounts
from demo.station_map_forecast import export_period, station_forecasts
from demo.station_map_nowcast import REPLAY, nowcast_replay
from demo.station_map_status import SourceMonitor, available_forecasts, export_csv, forecast_payload, verification_payload


STATIC = Path(__file__).with_name('station_map')
STATE = ROOT / 'data' / 'operational' / 'station_map_web'
WARD_BOUNDARIES = ROOT / 'data' / 'operational' / 'station_map_areas' / 'wards-48.geojson'
ROUTES = {
    '/': (STATIC / 'index.html', 'text/html; charset=utf-8'),
    '/login': (STATIC / 'login.html', 'text/html; charset=utf-8'),
    '/dashboard': (STATIC / 'dashboard.html', 'text/html; charset=utf-8'),
    '/map.css': (STATIC / 'map.css', 'text/css; charset=utf-8'),
    '/explore.css': (STATIC / 'explore.css', 'text/css; charset=utf-8'),
    '/areas.css': (STATIC / 'areas.css', 'text/css; charset=utf-8'),
    '/map.js': (STATIC / 'map.js', 'application/javascript; charset=utf-8'),
    '/areas.js': (STATIC / 'areas.js', 'application/javascript; charset=utf-8'),
    '/api/areas': (WARD_BOUNDARIES, 'application/geo+json; charset=utf-8'),
    '/portal.css': (STATIC / 'portal.css', 'text/css; charset=utf-8'),
    '/portal.js': (STATIC / 'portal.js', 'application/javascript; charset=utf-8'),
    '/dashboard.js': (STATIC / 'dashboard.js', 'application/javascript; charset=utf-8'),
}
MEMBER_APIS = ('/api/status', '/api/verification', '/api/export.csv', '/api/export-forecast.csv', '/api/admin/alerts')
AUTH_COMMANDS = ('/api/account/setup', '/api/account/login', '/api/account/logout')


class MapHandler(BaseHTTPRequestHandler):
    def respond(self, status, body, media_type, headers=None):
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
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def reply_json(self, value, status=200, cookie=None):
        self.respond(status, json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'),
                     'application/json; charset=utf-8', {'Set-Cookie': cookie} if cookie else None)

    def allowed_host(self):
        return (self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
                and self.headers.get('Sec-Fetch-Site') != 'cross-site')

    def user(self):
        return self.server.accounts.session_user(self.headers.get('Cookie'))

    def redirect(self, path):
        self.respond(303, b'', 'text/plain; charset=utf-8', {'Location': path})

    def do_GET(self):
        if not self.allowed_host():
            self.reply_json({'error': 'local_access_only'}, 403)
            return
        requested = urlsplit(self.path)
        path = requested.path
        if path == '/cuc-ngan':
            self.redirect('/?lead=h1')
            return
        user = self.user()
        if path == '/dashboard' and not user:
            self.redirect('/login')
            return
        if path == '/login' and user:
            self.redirect('/dashboard')
            return
        if path in MEMBER_APIS and not user:
            self.reply_json({'error': 'login_required'}, 401)
            return
        try:
            if path == '/api/account':
                self.reply_json(dict(username=user, setup_required=self.server.accounts.owner() is None))
            elif path == '/api/short-range':
                self.reply_json(forecast_payload(available_forecasts(), bool(user)))
            elif path == '/api/forecast':
                self.reply_json(station_forecasts(bool(user), self.server.monitor.hourly))
            elif path == '/api/nowcast-replay':
                self.reply_json(nowcast_replay(REPLAY, bool(user)))
            elif path == '/api/status':
                self.reply_json(self.server.monitor.status())
            elif path == '/api/verification':
                self.reply_json(verification_payload())
            elif path == '/api/admin/alerts':
                summary = parse_qs(requested.query).get('summary') == ['1']
                self.reply_json(self.server.monitor.alert_inbox(summary))
            elif path == '/api/export.csv':
                query = parse_qs(requested.query)
                try:
                    body, filename = export_csv(query.get('issue', [''])[0], int(query.get('day', ['0'])[0]))
                except ValueError:
                    self.reply_json({'error': 'unknown_issue_or_horizon'}, 404)
                else:
                    self.respond(200, body, 'text/csv; charset=utf-8',
                                 {'Content-Disposition': f'attachment; filename="{filename}"'})
            elif path == '/api/export-forecast.csv':
                query = parse_qs(requested.query)
                try:
                    body, filename = export_period(station_forecasts(True, self.server.monitor.hourly), query.get('issue', [''])[0],
                                                   query.get('lead', [''])[0], query.get('scope', ['common'])[0])
                except ValueError:
                    self.reply_json({'error': 'unknown_issue_or_horizon'}, 404)
                else:
                    self.respond(200, body, 'text/csv; charset=utf-8',
                                 {'Content-Disposition': f'attachment; filename="{filename}"'})
            elif path in ROUTES:
                file, media_type = ROUTES[path]
                self.respond(200, file.read_bytes(), media_type)
            else:
                self.reply_json({'error': 'not_found'}, 404)
        except (OSError, ValueError, sqlite3.Error):
            self.reply_json({'error': 'data_unavailable'}, 503)

    def object_body(self):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 4096 or self.headers.get('Transfer-Encoding'):
            raise ValueError('invalid_request')
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict):
            raise ValueError('invalid_request')
        return body

    def do_POST(self):
        origin = f'http://127.0.0.1:{self.server.server_port}'
        if not self.allowed_host() or self.headers.get('Origin') != origin:
            self.reply_json({'error': 'local_access_only'}, 403)
            return
        path = urlsplit(self.path).path
        if path not in (*AUTH_COMMANDS, '/api/source-check', '/api/admin/alerts/read'):
            self.reply_json({'error': 'not_found'}, 404)
            return
        if self.headers.get_content_type() != 'application/json':
            self.reply_json({'error': 'invalid_request'}, 415)
            return
        try:
            body = self.object_body()
        except (ValueError, OSError):
            self.reply_json({'error': 'invalid_request'}, 400)
            return
        if path in ('/api/source-check', '/api/admin/alerts/read'):
            if not self.user():
                self.reply_json({'error': 'login_required'}, 401)
            elif path == '/api/admin/alerts/read':
                identifier = body.get('id')
                if body.keys() == {'all'} and body['all'] is True:
                    identifier = None
                elif type(identifier) is not int or not 0 < identifier < 2**63:
                    self.reply_json({'error': 'invalid_request'}, 400)
                    return
                try:
                    self.server.monitor.alerts.mark_read(identifier)
                    self.reply_json(self.server.monitor.alerts.inbox(summary=True))
                except sqlite3.Error:
                    self.reply_json({'error': 'data_unavailable'}, 503)
            elif self.server.monitor.start_check():
                self.reply_json({'status': 'started'}, 202)
            else:
                self.reply_json({'error': 'source_check_recent'}, 429)
            return
        accounts = self.server.accounts
        if path == '/api/account/logout':
            self.reply_json({'status': 'signed_out'}, cookie=accounts.close_session(self.headers.get('Cookie')))
            return
        username = body.get('username')
        password = body.get('password')
        if not isinstance(username, str) or not isinstance(password, str):
            self.reply_json({'error': 'invalid_request'}, 400)
            return
        username = username.strip()
        if not 1 <= len(username) <= 32 or not 1 <= len(password) <= 128:
            self.reply_json({'error': 'invalid_request'}, 400)
            return
        try:
            password.encode('utf-8')
        except UnicodeError:
            self.reply_json({'error': 'invalid_request'}, 400)
            return
        if not accounts.begin_attempt():
            self.reply_json({'error': 'too_many_attempts'}, 429)
            return
        if path == '/api/account/setup':
            try:
                cookie = accounts.register(username, password)
            except AccountExists:
                self.reply_json({'error': 'account_exists'}, 409)
                return
            except ValueError as error:
                self.reply_json({'error': str(error)}, 400)
                return
        else:
            cookie = accounts.sign_in(username, password)
            if cookie is None:
                self.reply_json({'error': 'invalid_credentials'}, 401)
                return
        self.reply_json({'status': 'signed_in'}, cookie=cookie)


def main():
    parser = argparse.ArgumentParser(description='Dự báo mưa và theo dõi nguồn trên máy này.')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--state-dir', type=Path, default=STATE)
    args = parser.parse_args()
    state = args.state_dir.resolve()
    state.mkdir(parents=True, exist_ok=True)
    with ThreadingHTTPServer(('127.0.0.1', args.port), MapHandler) as server:
        server.accounts = Accounts(state / 'accounts.sqlite')
        server.monitor = SourceMonitor(state)
        print(f'http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
