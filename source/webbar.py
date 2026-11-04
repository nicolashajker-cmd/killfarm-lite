"""BARRE WEB : la barre Stream servie comme une page web sur TON PC (http://127.0.0.1:8777/).

Pourquoi : TikTok LIVE Studio capture mal les fenêtres de l'appli (noir, blanc, ou largeur 0). Avec cette page,
on ajoute une source « Lien » (TikTok LIVE Studio) ou « Navigateur » (OBS) : le fond est VRAIMENT transparent,
rien à capturer, et les chiffres se mettent à jour tout seuls (la page relit /data chaque seconde).

- Rien ne sort du PC : le serveur écoute seulement 127.0.0.1 (la machine elle-même).
- /            -> la page (tableau 1120 x 124, mis à l'échelle de la largeur de la source)
- /data        -> les chiffres du farm actif (JSON), préparés par l'appli (thread Tk) dans set_data()
- /img/<...>   -> images de l'appli (animal, badges), seulement dans le dossier Image
Options de l'adresse : ?fond=0.6 (opacité du fond, 0 = aucun fond, 1 = plein)."""
import json
import mimetypes
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config

PORTS = (8777, 8778, 8779, 8787, 8797)
_state = {"json": b'{"farm": null}'}
_server = None
port = None


def url():
    return f"http://127.0.0.1:{port}/" if port else None


def set_data(payload):
    """Appelé par l'appli à chaque affichage : dict -> JSON prêt à servir."""
    try:
        _state["json"] = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError):
        pass


def img_url(p):
    """Chemin d'une image de l'appli -> adresse /img/... (None si hors du dossier Image)."""
    if not p:
        return None
    try:
        rel = Path(p).resolve().relative_to(config.IMG_DIR.resolve())
    except (ValueError, OSError):
        return None
    return "/img/" + urllib.parse.quote(rel.as_posix())


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):                              # pas de console
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/barre", "/index.html"):
            return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/data":
            return self._send(200, _state["json"], "application/json; charset=utf-8")
        if path.startswith("/img/"):
            rel = urllib.parse.unquote(path[5:])
            root = config.IMG_DIR.resolve()
            try:
                f = (root / rel).resolve()
                f.relative_to(root)                         # jamais en dehors du dossier Image
                if f.is_file():
                    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                    return self._send(200, f.read_bytes(), ctype)
            except (ValueError, OSError):
                pass
        return self._send(404, b"404", "text/plain")


def start():
    """Lance le serveur (une fois). -> l'adresse, ou None si aucun port libre."""
    global _server, port
    if _server is not None:
        return url()
    for p in PORTS:
        try:
            _server = ThreadingHTTPServer(("127.0.0.1", p), _Handler)
        except OSError:
            continue
        _server.daemon_threads = True
        port = p
        threading.Thread(target=_server.serve_forever, daemon=True, name="webbar").start()
        return url()
    return None


def stop():
    global _server
    if _server is not None:
        try:
            _server.shutdown()
        except Exception:
            pass
        _server = None


PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>KillFarm Lite – Barre</title>
<style>
html,body{margin:0;padding:0;background:transparent;overflow:hidden}
#wrap{position:absolute;left:0;top:0;width:1120px;height:124px;transform-origin:0 0;
  font-family:"Segoe UI",Arial,sans-serif;color:var(--fg)}
.cut{clip-path:polygon(16px 0,calc(100% - 16px) 0,100% 16px,100% calc(100% - 16px),calc(100% - 16px) 100%,16px 100%,0 calc(100% - 16px),0 16px)}
#frame{position:absolute;left:0;right:0;top:20px;bottom:2px;background:var(--acc)}
#bg{position:absolute;inset:2px;background:var(--card);opacity:var(--op)}
#body{position:absolute;left:0;right:0;top:20px;bottom:2px;display:flex;align-items:center;padding:0 18px 0 20px}
.tab{position:absolute;top:0;height:24px;display:flex;align-items:center;font-size:12px;font-weight:700;
  clip-path:polygon(0 0,100% 0,calc(100% - 12px) 100%,12px 100%)}
#tl{left:24px;width:300px;background:var(--acc);color:var(--bg);padding-left:22px;box-sizing:border-box;letter-spacing:.6px}
#tr{right:24px;width:250px;background:var(--bg);color:var(--fg);justify-content:space-between;padding:0 24px;box-sizing:border-box}
#tr i{color:var(--acc);font-weight:400;font-size:11px}
#tr b{font-family:Bahnschrift,Arial;font-size:15px}
.pic{width:80px;height:80px;border-radius:50%;border:3px solid var(--acc);box-sizing:border-box;flex:none;
  background:var(--card) center/72% no-repeat;margin-right:14px}
.who{width:200px;flex:none;margin-right:18px;overflow:hidden}
.who b{display:block;font-size:20px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 2px 3px #000}
.who span{display:block;font-size:12px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.who em{display:flex;align-items:center;gap:5px;font-style:normal;font-size:12px;font-weight:700;color:var(--gold);margin-top:4px}
.who em img{width:18px;height:18px}
.blk{height:68px;border-radius:8px;background:var(--bg);border:1px solid var(--edge);margin-right:10px;flex:none;
  display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative}
.blk.main{border:2px solid var(--acc)}
.blk small{font-size:11px;font-weight:700;color:var(--dim);letter-spacing:.4px}
.blk b{font-family:Bahnschrift,Arial;font-weight:700;line-height:1.1}
.grades{flex:1;display:flex;justify-content:space-around;margin-left:6px}
.g{display:flex;flex-direction:column;align-items:center}
.g img{width:34px;height:34px}
.g b{font-family:Bahnschrift,Arial;font-size:16px;margin-top:2px}
.plus{position:absolute;right:6px;top:4px;font:700 18px Bahnschrift,Arial;color:var(--leaf);opacity:0}
.plus.on{animation:up 1.6s ease-out}
@keyframes up{0%{opacity:1;transform:translateY(0)}100%{opacity:0;transform:translateY(-22px)}}
#go{position:absolute;left:50%;top:58%;transform:translate(-50%,-50%);font:700 40px Bahnschrift,Arial;color:var(--gold);
  background:var(--card);border:3px solid var(--gold);border-radius:12px;padding:2px 24px;display:none}
#go.on{display:block;animation:blink .25s steps(2) 24}
@keyframes blink{50%{color:var(--fg)}}
#none{width:100%;text-align:center;font-size:18px;color:var(--dim)}
</style></head>
<body><div id="wrap"><div id="frame" class="cut"><div id="bg" class="cut"></div></div>
<div id="body"></div><div id="tl" class="tab"></div><div id="tr" class="tab"><i></i><b></b></div>
<div id="go">GREAT ONE !</div></div>
<script>
const q=new URLSearchParams(location.search);
const W=document.getElementById('wrap'),B=document.getElementById('body');
function fit(){W.style.transform='scale('+(innerWidth/1120)+')'}
addEventListener('resize',fit);fit();
let last=null;
function nf(n,lang){n=Math.round(n||0);return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g,lang=='en'?',':' ')}
function sn(n,lang){n=Math.round(n||0);if(n<10000)return nf(n,lang);const d=lang=='en'?'.':',';
  if(n<1e6)return(n/1000).toFixed(1).replace('.0','').replace('.',d)+'k';return(n/1e6).toFixed(2).replace('.',d)+'M'}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function clock(){const d=new Date();return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}
function draw(d){
  const op=q.has('fond')?Math.max(0,Math.min(1,parseFloat(q.get('fond'))||0)):d.opacity;
  const r=document.documentElement.style;for(const k in d.theme)r.setProperty('--'+k,d.theme[k]);r.setProperty('--op',op);
  document.getElementById('tl').textContent=d.labels.tab;
  document.querySelector('#tr i').textContent=d.sig;document.querySelector('#tr b').textContent=clock();
  const f=d.farm;
  if(!f){B.innerHTML='<div id="none">'+esc(d.none)+'</div>';last=null;return}
  const L=d.labels,G=d.grade_cols;
  let h='<div class="pic" style="background-image:url('+(f.img||'')+')"></div>'+
    '<div class="who"><b>'+esc(f.name)+'</b><span>'+esc(f.reserve)+'</span><em>'+(d.badges[5]?'<img src="'+d.badges[5]+'">':'')+
    esc(f.go_label)+'</em></div>';
  const bl=[[L.since,nf(f.since,d.lang),'var(--acc)',176,34,'main'],[L.last_go,f.last_go?nf(f.last_go,d.lang):'—','var(--gold)',128,26,''],
            [L.count,nf(f.count,d.lang),'var(--fg)',128,26,'']];
  for(const b of bl)h+='<div class="blk '+b[5]+'" style="width:'+b[3]+'px"><small>'+esc(b[0])+'</small><b style="color:'+b[2]+
    ';font-size:'+b[4]+'px">'+b[1]+'</b>'+(b[5]?'<span class="plus" id="p1">+1</span>':'')+'</div>';
  h+='<div class="grades">';
  for(let i=0;i<6;i++)h+='<div class="g">'+(d.badges[i]?'<img src="'+d.badges[i]+'">':'')+'<b style="color:'+G[i]+'">'+sn(f.grades[i],d.lang)+'</b></div>';
  B.innerHTML=h+'</div>';
  if(last&&last.key==f.key){
    if(f.count>last.count){const p=document.getElementById('p1');if(p)p.classList.add('on')}
    if(f.go>last.go){const g=document.getElementById('go');g.classList.remove('on');void g.offsetWidth;g.classList.add('on')}
  }
  last={key:f.key,count:f.count,go:f.go};
}
let prev='';
async function tick(){try{const r=await fetch('/data',{cache:'no-store'});const t=await r.text();
  if(t!==prev){prev=t;draw(JSON.parse(t))}else{document.querySelector('#tr b').textContent=clock()}}catch(e){}}
tick();setInterval(tick,1000);
</script></body></html>
"""
