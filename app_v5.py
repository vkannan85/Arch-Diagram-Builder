from flask import Flask, request, render_template_string, Response
import re, html, json, time
app=Flask(__name__)
CIDR=r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'
def esc(v): return html.escape(str(v or 'Not specified'))
def cidr_after(t,n):
 m=re.search(re.escape(n)+r'.{0,120}?('+CIDR+r')',t,re.I|re.S); return m.group(1) if m else None
def parse_requirement(t):
 names=re.findall(r'\bSpoke\s*\d+[- ]?VNet\b|\bSpoke\d+-VNet\b',t,re.I) or ['Spoke1-VNet','Spoke2-VNet']; spokes=[]
 for raw in names:
  n=re.sub(r'\s+','',raw); n=n.replace('VNet','-VNet') if '-' not in n else n; n=n.replace('--','-')
  if any(x['name'].lower()==n.lower() for x in spokes): continue
  i=len(spokes)+1; vm=(re.search(r'\bVM0?%d\b'%i,t,re.I).group(0).upper() if re.search(r'\bVM0?%d\b'%i,t,re.I) else 'VM%02d'%i)
  sm=re.search(re.escape(vm)+r'.{0,140}?('+CIDR+r')',t,re.I|re.S)
  spokes.append({'name':n,'cidr':cidr_after(t,n),'vm':vm,'subnet':sm.group(1) if sm else None})
 return {'title':'Hub-and-Spoke Network Architecture','subtitle':'Secure connectivity between Azure workloads and On-Premises infrastructure','hub':{'name':'Hub-VNet','cidr':cidr_after(t,'Hub-VNet')},'onprem':{'name':'On-Premises Datacentre','cidr':None},'spokes':spokes,'settings':{'forwarded':bool(re.search('forwarded traffic',t,re.I)),'gateway_transit':bool(re.search('gateway transit',t,re.I)),'remote_gateway':bool(re.search('remote gateway',t,re.I))},'source':t}
def layout(m):
 n=max(1,len(m['spokes'])); sh=245; gap=34; top=130; H=max(920,top+n*(sh+gap)+190)
 return {'w':1800,'h':H,'onprem':(55,250,250,360),'er':(350,390),'hub':(500,145,600,max(600,n*(sh+gap)-20)),'spokes':[(1210,top+i*(sh+gap),520,sh) for i in range(n)]}
def icon(k,x,y):
 # Asset adapter: V5 uses this one boundary for icons. Official Microsoft SVGs can be dropped in without changing layout/export logic.
 if k=='firewall': return f'<g transform="translate({x},{y})"><path d="M38 2l34 12v25c0 23-15 38-34 47C19 77 4 62 4 39V14z" fill="#0078d4"/><path d="M18 25h40v9H18zm0 14h18v9H18zm23 0h17v9H41zm-23 14h40v9H18z" fill="white"/></g>'
 if k in ('gateway','expressroute'): return f'<g transform="translate({x},{y})"><circle cx="38" cy="38" r="36" fill="#0078d4"/><path d="M15 38h46M25 25L14 38l11 13M51 25l11 13-11 13" fill="none" stroke="white" stroke-width="5"/></g>'
 return f'<g transform="translate({x},{y})"><rect width="76" height="54" rx="5" fill="#0078d4"/><rect x="8" y="8" width="60" height="36" fill="white"/><path d="M30 58h16v9H30zM19 67h38v5H19z" fill="#0078d4"/></g>'
def svg(m):
 L=layout(m); W,H=L['w'],L['h']; hx,hy,hw,hh=L['hub']; ox,oy,ow,oh=L['onprem']; ex,ey=L['er']
 def t(x,y,s,z=18,w=400,a='start',f='#17324d'): return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial" font-size="{z}" font-weight="{w}" text-anchor="{a}" fill="{f}">{esc(s)}</text>'
 def b(x,y,w,h,s,f,rx=18,sw=2): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" stroke="{s}" stroke-width="{sw}"/>'
 A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker></defs><rect width="100%" height="100%" fill="white"/>',t(55,60,m['title'],36,700),t(55,91,m['subtitle'],18,400,f='#5d7185'),b(ox,oy,ow,oh,'#8292a2','#f6f8fa'),t(ox+ow/2,oy+45,'On-Premises',23,700,'middle'),t(ox+ow/2,oy+75,'Datacentre',17,400,'middle','#5d7185'),'<g fill="#dfe5ea" stroke="#63778a" stroke-width="3"><rect x="95" y="365" width="45" height="130" rx="4"/><rect x="157" y="365" width="45" height="130" rx="4"/><rect x="219" y="365" width="45" height="130" rx="4"/></g>',t(ox+ow/2,oy+292,'Corporate Network',17,700,'middle'),t(ox+ow/2,oy+322,'CIDR not specified',14,400,'middle','#718295'),icon('expressroute',ex,ey),t(ex+38,ey+100,'ExpressRoute',18,700,'middle'),t(ex+38,ey+124,'Circuit',16,400,'middle'),f'<path d="M{ox+ow} {ey+38}H{ex}" stroke="#0078d4" stroke-width="4" marker-end="url(#a)"/>',b(hx,hy,hw,hh,'#0078d4','#f4faff',20,3),t(hx+30,hy+43,'Hub Virtual Network',27,700),t(hx+30,hy+75,f"{m['hub']['name']} • {m['hub']['cidr'] or 'CIDR not specified'}",17,400,f='#526a80'),b(hx+55,hy+125,hw-110,190,'#75b9e7','#fff',14),t(hx+80,hy+158,'GatewaySubnet',18,700),t(hx+80,hy+184,'CIDR not specified',14,400,f='#718295'),icon('gateway',hx+260,hy+198),t(hx+298,hy+295,'ExpressRoute Gateway',18,700,'middle'),b(hx+55,hy+355,hw-110,190,'#75b9e7','#fff',14),t(hx+80,hy+388,'AzureFirewallSubnet',18,700),t(hx+80,hy+414,'CIDR not specified',14,400,f='#718295'),icon('firewall',hx+260,hy+425),t(hx+298,hy+525,'Azure Firewall',18,700,'middle'),f'<path d="M{ex+76} {ey+38}H{hx+55}V{hy+220}" fill="none" stroke="#0078d4" stroke-width="4" marker-end="url(#a)"/>']
 bus=hx+hw+55; A.append(f'<path d="M{hx+hw} {hy+270}H{bus}" stroke="#0078d4" stroke-width="4"/>')
 for i,(sp,(x,y,w,h)) in enumerate(zip(m['spokes'],L['spokes']),1):
  cy=y+h/2; A += [f'<path d="M{bus} {hy+270}V{cy}H{x}" fill="none" stroke="#0078d4" stroke-width="4" marker-end="url(#a)"/>',b(x,y,w,h,'#39a869','#f5fff8',18,3),t(x+28,y+40,f'Spoke Virtual Network {i:02d}',22,700),t(x+28,y+69,f"{sp['name']} • {sp['cidr'] or 'CIDR not specified'}",16,400,f='#526a80'),b(x+35,y+95,w-70,112,'#8dc9ed','#fff',12),t(x+58,y+128,'Workload Subnet',16,700),t(x+58,y+153,sp['subnet'] or 'CIDR not specified',14,400,f='#718295'),icon('vm',x+w-150,y+118),t(x+w-112,y+198,f"{sp['vm']} • Windows Server",14,700,'middle')]
 A += [t(bus+12,hy+245,'VNet Peering',15,700),t(55,H-115,'Architecture notes',18,700),t(55,H-82,'• Unspecified CIDRs are deliberately not invented.',15),t(55,H-54,'• Gateway transit / remote gateway and forwarded traffic are represented as peering policy.',15),t(55,H-26,'• Add UDRs when spoke traffic must be forced through Azure Firewall.',15),'</svg>']; return ''.join(A)
def drawio(m):
 L=layout(m); hx,hy,hw,hh=L['hub']; ox,oy,ow,oh=L['onprem']; ex,ey=L['er']
 def c(i,v,x,y,w,h,style,parent='1'): return f'<mxCell id="{i}" value="{html.escape(v)}" style="{style}" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
 R=['<mxCell id="0"/><mxCell id="1" parent="0"/>',c('op','On-Premises Datacentre',ox,oy,ow,oh,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f6f8fa;strokeColor=#8292a2;fontSize=18;'),c('er','ExpressRoute Circuit',ex,ey,76,76,'ellipse;html=1;fillColor=#0078d4;fontColor=#ffffff;'),c('hub',f"Hub Virtual Network&#xa;{m['hub']['name']} • {m['hub']['cidr'] or 'CIDR not specified'}",hx,hy,hw,hh,'swimlane;rounded=1;html=1;startSize=80;container=1;collapsible=0;strokeColor=#0078d4;fillColor=#f4faff;fontSize=19;'),c('gw','GatewaySubnet&#xa;CIDR not specified&#xa;ExpressRoute Gateway',55,125,490,190,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#75b9e7;fillColor=#ffffff;fontSize=16;','hub'),c('fw','AzureFirewallSubnet&#xa;CIDR not specified&#xa;Azure Firewall',55,355,490,190,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#75b9e7;fillColor=#ffffff;fontSize=16;','hub')]
 for i,(sp,(x,y,w,h)) in enumerate(zip(m['spokes'],L['spokes']),1): R += [c(f's{i}',f"Spoke Virtual Network {i:02d}&#xa;{sp['name']} • {sp['cidr'] or 'CIDR not specified'}",x,y,w,h,'swimlane;rounded=1;html=1;startSize=75;container=1;collapsible=0;strokeColor=#39a869;fillColor=#f5fff8;fontSize=17;'),c(f'vm{i}',f"Workload Subnet • {sp['subnet'] or 'CIDR not specified'}&#xa;{sp['vm']} • Windows Server",35,95,w-70,112,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#8dc9ed;fillColor=#ffffff;fontSize=15;',f's{i}')]
 edges=[('e1','op','er','ExpressRoute'),('e2','er','gw','Private connectivity')]+[(f'ep{i}','hub',f's{i}','VNet Peering') for i in range(1,len(m['spokes'])+1)]
 for eid,s,d,l in edges: R.append(f'<mxCell id="{eid}" value="{l}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#0078d4;strokeWidth=3;endArrow=block;" edge="1" parent="1" source="{s}" target="{d}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="V5 Azure Architecture"><mxGraphModel page="1" pageWidth="1800" pageHeight="'+str(L['h'])+'"><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
PAGE='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Studio V5</title><style>body{margin:0;font-family:Arial;background:#07111f;color:#eef5ff}.top{padding:16px 22px;background:#0c1a2d;font-weight:800;font-size:20px}.top b{color:#39a8ff}.grid{display:grid;grid-template-columns:380px 1fr;min-height:calc(100vh - 58px)}.side{padding:18px;background:#0c1a2d}.main{padding:18px}.card{background:#11243b;border:1px solid #29415e;border-radius:14px;padding:15px}textarea{width:100%;height:390px;box-sizing:border-box;background:#071522;color:white;border:1px solid #395675;border-radius:10px;padding:12px}.btn{display:inline-block;margin:10px 5px 0 0;background:#1688f8;color:white;border:0;border-radius:9px;padding:11px 15px;font-weight:700;text-decoration:none}.secondary{background:#29415e}.canvas{background:white;border-radius:14px;overflow:auto;height:82vh}.canvas img{display:block;max-width:none}@media(max-width:850px){.grid{display:block}.side,.main{padding:10px}.canvas{height:65vh}}</style></head><body><div class="top"><b>Azure</b> Architecture Studio <small>V5</small></div><div class="grid"><div class="side"><div class="card"><form method="post"><h3>Architecture requirement</h3><textarea name="req">{{req}}</textarea><button class="btn">Generate V5 Architecture</button></form>{% if has %}<a class="btn secondary" href="/v5.svg" download>SVG</a><a class="btn secondary" href="/v5.drawio" download>Draw.io</a><a class="btn secondary" href="/v5/model" download>JSON</a>{% endif %}</div></div><div class="main"><div class="canvas">{% if has %}<img src="/v5.svg?t={{stamp}}">{% else %}<div style="color:#456;padding:30px">Enter a requirement and generate the V5 architecture.</div>{% endif %}</div></div></div></body></html>'''
CURRENT=None
@app.route('/',methods=['GET','POST'])
def home():
 global CURRENT
 req=request.form.get('req','') if request.method=='POST' else (CURRENT['source'] if CURRENT else '')
 if request.method=='POST' and req.strip(): CURRENT=parse_requirement(req)
 return render_template_string(PAGE,req=req,has=CURRENT is not None,stamp=int(time.time()))
@app.route('/v5.svg')
def rsvg(): return Response(svg(CURRENT),mimetype='image/svg+xml',headers={'Content-Disposition':'inline; filename=architecture-v5.svg'}) if CURRENT else Response('No diagram',404)
@app.route('/v5.drawio')
def rdraw(): return Response(drawio(CURRENT),mimetype='application/xml',headers={'Content-Disposition':'attachment; filename=architecture-v5.drawio'}) if CURRENT else Response('No diagram',404)
@app.route('/v5/model')
def rmodel(): return Response(json.dumps(CURRENT,indent=2),mimetype='application/json',headers={'Content-Disposition':'attachment; filename=architecture-v5.json'}) if CURRENT else Response('{}',404)
@app.route('/health')
def health(): return {'ok':True,'version':'v5','renderer':'model-layout-svg-drawio'}
if __name__=='__main__': app.run(host='0.0.0.0',port=3000)
