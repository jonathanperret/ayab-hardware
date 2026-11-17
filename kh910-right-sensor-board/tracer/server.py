import http.server, json, os, sys, time, shutil
ROOT=os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store'); super().end_headers()
    def do_POST(self):
        if self.path!='/state.json': self.send_error(404); return
        n=int(self.headers.get('Content-Length',0)); body=self.rfile.read(n)
        try: json.loads(body)
        except Exception: self.send_error(400,'bad json'); return
        os.makedirs('backups',exist_ok=True)
        if os.path.exists('state.json'): shutil.copy('state.json',f'backups/state-{time.strftime("%H%M%S")}.json')
        open('state.json.tmp','wb').write(body); os.replace('state.json.tmp','state.json')
        self.send_response(204); self.end_headers()
    def log_message(self,*a): pass
port=int(sys.argv[1]) if len(sys.argv)>1 else 8765
print(f'http://localhost:{port}/'); http.server.ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
