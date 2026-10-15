"""Loopback-only research preview. Never package private workbook assets for hosting."""
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .evidence_checks import require


def load_assets(root, workbook_directory):
    root, workbook_directory = root.resolve(), workbook_directory.resolve()
    registry = json.loads((workbook_directory / 'registry.json').read_text())
    qa = json.loads((workbook_directory / 'qa.json').read_text())
    require(registry['visibility'] == 'private' and registry['public_release_approved'] is False,
            'Private workbook registry required')
    require(qa['status'] == 'PASS' and qa['sha256'] == registry['sha256'], 'Workbook QA missing or stale')
    require(registry['filename'] == 'Credit-Risk-Strategy-Lab-Private.xlsx', 'Unexpected workbook filename')
    assets = {}
    for route, filename, content_type, digest in [
        ('/workbook/preview.json', 'preview.json', 'application/json; charset=utf-8', registry['preview_sha256']),
        ('/workbook/download', registry['filename'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', registry['sha256']),
    ]:
        data = (workbook_directory / filename).read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, 'Workbook artifact changed after QA')
        assets[route] = (data, content_type)
    snapshot = json.loads((root / 'site/dist/data.json').read_text())
    require(snapshot['pipeline_run'] == registry['pipeline_run'], 'Website and workbook use different runs')
    assets['/data.json'] = (json.dumps(snapshot).encode('utf-8'), 'application/json; charset=utf-8')
    return assets


def make_handler(root, workbook_directory):
    private_assets = load_assets(root, workbook_directory)
    site_dir = root.resolve() / 'site/dist'
    static = {'/': ('index.html', 'text/html; charset=utf-8'),
              '/index.html': ('index.html', 'text/html; charset=utf-8'),
              '/style.css': ('style.css', 'text/css; charset=utf-8'),
              '/dashboard-fixes.css': ('dashboard-fixes.css', 'text/css; charset=utf-8'),
              '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
              '/dashboard.js': ('dashboard.js', 'text/javascript; charset=utf-8'),
              '/workbook.js': ('workbook.js', 'text/javascript; charset=utf-8'),
              '/data.json': ('data.json', 'application/json; charset=utf-8')}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond(False)

        def do_HEAD(self):
            self.respond(True)

        def respond(self, head):
            host = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.send_error(403)
                return
            route = urlsplit(self.path).path
            if route in private_assets:
                body, content_type = private_assets[route]
            elif route in static:
                filename, content_type = static[route]
                body = (site_dir / filename).read_bytes()
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            if route == '/workbook/download':
                self.send_header('Content-Disposition', 'attachment; filename="Credit-Risk-Strategy-Lab-Private.xlsx"')
            self.end_headers()
            if not head:
                self.wfile.write(body)

    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook-directory', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    handler = make_handler(root, args.workbook_directory)
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Private research preview: http://127.0.0.1:{server.server_port}/', flush=True)
        server.serve_forever()
