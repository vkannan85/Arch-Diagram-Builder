from flask import Flask, request, render_template_string, Response
import re, html, json

app = Flask(__name__)
CIDR = r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'

# V5: canonical architecture model -> automatic layout -> SVG.
# Icon adapter is isolated so official Microsoft SVG assets can replace these
# fallbacks without changing the architecture/layout model.

def esc(v): return html.escape(str(v or 'Not specified'))
def cidr_after(text, name):
    m = re.search(re.escape(name) + r'.{0,120}?(' + CIDR + r')', text, re.I | re.S)
    return m.group(1) if m else None

def parse_requirement(text):
    spokes=[]
    names=re.findall(r'\b(Spoke\s*\d+[- ]?VNet|Spoke\d+-VNet)\b', text, re.I)
    if not names: names=['Spoke1-VNet','Spoke2-VNet']
    seen=[]
    for raw in names:
        n=re.sub(r'\s+','',raw).replace('VNet','-VNet') if '-' not in raw else raw
        n=n.replace('--','-')
        if n.lower() in [x.lower() for x in seen]: continue
        seen.append(n)
        idx=len(seen)
        vm_match=re.search(r'\bVM0?%d\b' % idx,text,re.I)
        vm=vm_match.group(0).upper() if vm_match else 'VM%02d'%idx
        sm=re.search(re.escape(vm)+r'.{0,140}?('+CIDR+r')',text,re.I|re.S)
        spokes.append({'name':n,'cidr':cidr_after(text,n),'vm':vm,'subnet':sm.group(1) if sm else None})
    return {
      'title':'Hub-and-Spoke Network Architecture',
      'subtitle':'Secure connectivity between Azure workloads and On-Premises infrastructure',
      'hub':{'name':'Hub-VNet','cidr':cidr_after(text,'Hub-VNet')},
      'onprem':{'name':'On-Premises Datacentre','cidr':None},
      'spokes':spokes,
      'services':['ExpressRoute Circuit','ExpressRoute Gateway','Azure Firewall'],
      'settings':{
        'forwarded':bool(re.search(r'forwarded traffic',text,re.I)),
        'gateway_transit':bool(re.search(r'gateway transit',text,re.I)),
        'remote_gateway':bool(re.search(r'remote gateway',text,re.I))
      }, 'source':text
    }

def icon(kind,x,y):
    # V5 fallback symbols; official Azure SVG asset adapter lands next.
    if kind=='firewall':
        return f'<g transform="translate({x},{y})"><path d="M38 2l34 12v25c0 23-15 38-34 47C19 77 4 62 4 39V14z" fill="#0078d4"/><path d="M18 25h40v9H18zm0 14h18v9H18zm23 0h17v9H41zm-23 14h40v9H18z" fill="white"/></g>'
    if kind=='gateway':
        return f'<g transform="translate({x},{y})"><circle cx="38" cy="38" r="36" fill="#0078d4"/><path d="M16 38h44M38 16v44M25 25L15 38l10 13M51 25l10 13-10 13" fill="none" stroke="white" stroke-width="5"/></g>'
    if kind=='expressroute':
        return f'<g transform="translate({x},{y})"><circle cx="38" cy="38" r="36" fill="#0078d4"/><path d="M15 38h46M25 25L14 38l11 13M51 25l11 13-11 13" fill="none" stroke="white" stroke-width="5"/></g>'
    return f'<g transform="translate({x},{y})"><rect width="76" height="54" rx="5" fill="#0078d4"/><rect x="8" y="8" width="60" height="36" fill="white"/><path d="M30 58h16v9H30zM19 67h38v5H19z" fill="#0078d4"/></g>'

def layout(model):
    n=max(1,len(model['spokes']))
    W=1800; top=130; spoke_h=245; gap=34
    H=max(920, top+n*(spoke_h+gap)+190)
    return {'w':W,'h':H,'onprem':(55,250,250,360),'er':(350,390),'hub':(500,145,600,max(600,n*(spoke_h+gap)-20)),
            'spokes':[(1210,top+i*(spoke_h+gap),520,spoke_h) for i in range(n)]}

def svg(model):
    L=layout(model); W,H=L['w'],L['h']; hub=model['hub']
    def t(x,y,s,size=18,w=400,a='start',fill='#17324d'): return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial" font-size="{size}" font-weight="{w}" text-anchor="{a}" fill="{fill}">{esc(s)}</text>'
    def box(x,y,w,h,stroke,fill,rx=18,sw=2): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker></defs>',f'<rect width="{W}" height="{H}" fill="#fff"/>',
       t(55,60,model['title'],36,700),t(55,91,model['subtitle'],18,400,fill='#5d7185')]
    ox,oy,ow,oh=L['onprem']; a += [box(ox,oy,ow,oh,'#8292a2','#f6f8fa'),t(ox+ow/2,oy+45,'On-Premises',23,700,'middle'),t(ox+ow/2,oy+75,'Datacentre',17,400,'middle','#5d7185'),'<g fill="#dfe5ea" stroke="#63778a" stroke-width="3"><rect x="95" y="365" width="45" height="130" rx="4"/><rect x="157" y="365" width="45" height="130" rx="4"/><rect x="219" y="365" width="45" height="130" rx="4"/></g>',t(ox+ow/2,oy+292,'Corporate Network',17,700,'middle'),t(ox+ow/2,oy+322,'CIDR not specified',14,400,'middle','#718295')]
    ex,ey=L['er']; a += [icon('expressroute',ex,ey),t(ex+38,ey+100,'ExpressRoute',18,700,'middle'),t(ex+38,ey+124,'Circuit',16,400,'middle'),f'<path d="M{ox+ow} {ey+38}H{ex}" stroke="#0078d4" stroke-width="4" marker-end="url(#arr)"/>']
    hx,hy,hw,hh=L['hub']; a += [box(hx,hy,hw,hh,'#0078d4','#f4faff',20,3),t(hx+30,hy+43,'Hub Virtual Network',27,700),t(hx+30,hy+75,f"{hub['name']}  •  {hub['cidr'] or 'CIDR not specified'}",17,400,fill='#526a80')]
    a += [box(hx+55,hy+125,hw-110,190,'#75b9e7','#fff',14),t(hx+80,hy+158,'GatewaySubnet',18,700),t(hx+80,hy+184,'CIDR not specified',14,400,fill='#718295'),icon('gateway',hx+260,hy+198),t(hx+298,hy+295,'ExpressRoute Gateway',18,700,'middle')]
    a += [box(hx+55,hy+355,hw-110,190,'#75b9e7','#fff',14),t(hx+80,hy+388,'AzureFirewallSubnet',18,700),t(hx+80,hy+414,'CIDR not specified',14,400,fill='#718295'),icon('firewall',hx+260,hy+425),t(hx+298,hy+525,'Azure Firewall',18,700,'middle')]
    a += [f'<path d="M{ex+76} {ey+38}H{hx+55}V{hy+220}" fill="none" stroke="#0078d4" stroke-width="4" marker-end="url(#arr)"/>']
    busx=hx+hw+55; a += [f'<path d="M{hx+hw} {hy+270}H{busx}" stroke="#0078d4" stroke-width="4"/>']
    for i,(sp,(x,y,w,h)) in enumerate(zip(model['spokes'],L['spokes']),1):
        cy=y+h/2
        a += [f'<path d="M{busx} {hy+270}V{cy}H{x}" fill="none" stroke="#0078d4" stroke-width="4" marker-end="url(#arr)"/>',box(x,y,w,h,'#39a869','#f5fff8',18,3),t(x+28,y+40,f'Spoke Virtual Network {i:02d}',22,700),t(x+28,y+69,f"{sp['name']}  •  {sp['cidr'] or 'CIDR not specified'}",16,400,fill='#526a80'),box(x+35,y+95,w-70,112,'#8dc9ed','#fff',12),t(x+58,y+128,'Workload Subnet',16,700),t(x+58,y+153,sp['subnet'] or 'CIDR not specified',14,400,fill='#718295'),icon('vm',x+w-150,y+118),t(x+w-112,y+198,f"{sp['vm']} • Windows Server",14,700,'middle')]
    a += [t(busx+12,hy+245,'VNet Peering',15,700),t(55,H-115,'Architecture notes',18,700),t(55,H-82,'• Unspecified CIDRs are deliberately not invented.',15),t(55,H-54,'• Gateway transit / remote gateway and forwarded traffic are represented as peering policy.',15),t(55,H-26,'• Add UDRs when spoke traffic must be forced through Azure Firewall.',15)]
    a.append('</svg>'); return ''.join(a)

PAGE='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Studio V5</title><style>body{margin:0;font-family:Arial;background:#07111f;color:#eef5ff}.top{padding:16px 22px;background:#0c1a2d;font-weight:800;font-size:20px}.top b{color:#39a8ff}.grid{display:grid;grid-template-columns:380px 1fr;min-height:calc(100vh - 58px)}.side{padding:18px;background:#0c1a2d}.main{padding:18px}.card{background:#11243b;border:1px solid #29415e;border-radius:14px;padding:15px}textarea{width:100%;height:420px;box-sizing:border-box;background:#071522;color:white;border:1px solid #395675;border-radius:10px;padding:12px}.btn{margin-top:10px;background:#1688f8;color:white;border:0;border-radius:9px;padding:11px 15px;font-weight:700}.canvas{background:white;border-radius:14px;overflow:auto;height:82vh}.canvas img{display:block;max-width:none}@media(max-width:850px){.grid{display:block}.side{padding:10px}.main{padding:10px}.canvas{height:65vh}}</style></head><body><div class="top"><b>Azure</b> Architecture Studio <span style="font-size:12px">V5 Preview</span></div><div class="grid"><div class="side"><div class="card"><form method="post"><h3>Architecture requirement</h3><textarea name="req">{{req}}</textarea><button class="btn">Generate V5 Architecture</button></form></div></div><div class="main"><div class="canvas">{% if has %}<img src="/v5.svg?t={{stamp}}">{% else %}<div style="color:#456;padding:30px">Enter a requirement and generate the V5 architecture.</div>{% endif %}</div></div></div></body></html>'''
CURRENT=None
@app.route('/',methods=['GET','POST'])
def home():
    global CURRENT
    req=request.form.get('req','') if request.method=='POST' else (CURRENT['source'] if CURRENT else '')
    if request.method=='POST' and req.strip(): CURRENT=parse_requirement(req)
    import time
    return render_template_string(PAGE,req=req,has=CURRENT is not None,stamp=int(time.time()))
@app.route('/v5.svg')
def v5svg():
    if not CURRENT: return Response('No diagram',status=404)
    return Response(svg(CURRENT),mimetype='image/svg+xml')
@app.route('/v5/model')
def model():
    if not CURRENT: return Response('{}',mimetype='application/json')
    return Response(json.dumps(CURRENT,indent=2),mimetype='application/json')
@app.route('/health')
def health(): return {'ok':True,'version':'v5','renderer':'model-layout-svg'}

if __name__=='__main__': app.run(host='0.0.0.0',port=3000)
