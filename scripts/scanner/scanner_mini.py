#!/usr/bin/env python3
import sys,json,urllib.request,subprocess,http.server,threading,queue,socket,signal
R='Einkaufsliste'
P=8770
def lookup(b):
 try:
  req=urllib.request.Request('https://world.openfoodfacts.org/api/v2/product/'+b+'.json?fields=product_name_de,product_name,brands',headers={'User-Agent':'J/1'})
  d=json.loads(urllib.request.urlopen(req,timeout=8).read())
  if d.get('status')==1:
   p=d['product']
   return(p.get('product_name_de')or p.get('product_name')or p.get('brands','')).strip()or None
 except:pass
def remind(n):
 # osascript argv: Produktname als Argument – kein Escaping nötig
 scpt='on run argv\nset i to item 1 of argv\nset l to item 2 of argv\ntell application "Reminders"\nif not (exists list l) then\nmake new list with properties {name:l}\nend if\nmake new reminder at end of list l with properties {name:i}\nend tell\nend run'
 r=subprocess.run(['osascript','-e',scpt,n,R],capture_output=True,text=True)
 if r.returncode!=0:print('  Reminders-Fehler:',r.stderr.strip()or'Keine Berechtigung?')
 return r.returncode==0
class H(http.server.BaseHTTPRequestHandler):
 def __init__(self,q,*a,**kw):self._q=q;super().__init__(*a,**kw)
 def do_POST(self):
  self._q.put(self.rfile.read(int(self.headers.get('Content-Length',0))).decode())
  self.send_response(200);self.end_headers();self.wfile.write(b'OK')
 def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'OK')
 def log_message(self,*_):pass
signal.signal(signal.SIGINT,lambda*_:(print('\nBeendet.'),sys.exit(0)))
q=queue.Queue()
srv=http.server.HTTPServer(('0.0.0.0',P),lambda*a,**kw:H(q,*a,**kw))
threading.Thread(target=srv.serve_forever,daemon=True).start()
try:s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));ip=s.getsockname()[0];s.close()
except:ip='unbekannt'
print('='*44)
print('  Jarvis Scanner [Netzwerk]')
print('='*44)
print('  Mac-IP:',ip,'  Port:',P)
print('  Bereit - warte auf Pi ...')
print()
while True:
 b=q.get().strip()
 if not b:continue
 print('  Scan:',b,end=' ',flush=True)
 n=lookup(b)
 if not n:
  print('(unbekannt)')
  try:n=input('  Name: ').strip()
  except:continue
 if n and remind(n):print('-> OK:',n)
 else:print('-> Fehler Reminders')
