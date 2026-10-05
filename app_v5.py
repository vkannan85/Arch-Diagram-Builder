from flask import Flask,request,render_template_string,Response
import re,html,json,time,urllib.request,zipfile,io,base64
app=Flask(__name__); CURRENT=None
CIDR=r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'
ICON_ZIP='https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons_V24.zip'; ICONS={}
def esc(v): return html.escape(str(v or 'Not specified'))
def cidr_after(t,n):
 m=re.search(re.escape(n)+r'.{0,140}?('+CIDR+r')',t,re.I|re.S); return m.group(1) if m else None
def parse_requirement(t):
 names=re.findall(r'\bSpoke\s*\d+[- ]?VNet\b|\bSpoke\d+-VNet\b',t,re.I) or ['Spoke1-VNet','Spoke2-VNet']; spokes=[]
 for raw in names:
  n=re.sub(r'\s+','',raw); n=n.replace('VNet','-VNet') if '-' not in n else n; n=n.replace('--','-')
  if any(x['name'].lower()==n.lower() for x in spokes): continue
  i=len(spokes)+1; mm=re.search(r'\bVM0?%d\b'%i,t,re.I); vm=mm.group(0).upper() if mm else 'VM%02d'%i
  sm=re.search(re.escape(vm)+r'.{0,160}?('+CIDR+r')',t,re.I|re.S)
  spokes.append({'name':n,'cidr':cidr_after(t,n),'vm':vm,'subnet':sm.group(1) if sm else None})
 return {'title':'Hub-and-Spoke Network Architecture','subtitle':'Secure connectivity between Azure workloads and On-Premises infrastructure','hub':{'name':'Hub-VNet','cidr':cidr_after(t,'Hub-VNet')},'onprem':{'name':'On-Premises Datacentre','cidr':None},'spokes':spokes,'settings':{'forwarded':bool(re.search('forwarded traffic',t,re.I)),'gateway_transit':bool(re.search('gateway transit',t,re.I)),'remote_gateway':bool(re.search('remote gateway',t,re.I))},'source':t}
def load_icons():
 global ICONS
 if ICONS:return
 try:
  data=urllib.request.urlopen(ICON_ZIP,timeout=20).read(); z=zipfile.ZipFile(io.BytesIO(data)); files=[n for n in z.namelist() if n.lower().endswith('.svg')]
  wanted={'firewall':['firewalls.svg'],'gateway':['virtual network gateways.svg','virtual-network-gateways.svg'],'expressroute':['expressroute circuits.svg','expressroute-circuits.svg'],'vm':['virtual machines.svg','virtual-machines.svg','windows virtual desktop.svg']}
  for k,terms in wanted.items():
   hit=next((n for n in files if any(n.lower().endswith(x) for x in terms)),None)
   if hit: ICONS[k]=base64.b64encode(z.read(hit)).decode()
 except Exception as e: print('Azure icon pack fallback:',e)
def icon(k,x,y,w=76,h=76):
 load_icons()
 if k in ICONS:return f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="data:image/svg+xml;base64,{ICONS[k]}"/>'
 return f'<g transform="translate({x},{y})"><rect width="{w}" height="{h}" rx="12" fill="#0078d4"/><text x="{w/2}" y="{h/2+6}" text-anchor="middle" fill="white" font-family="Arial" font-size="15">Azure</text></g>'
def datacentre(x,y):
 return f'''<g transform="translate({x},{y})"><rect width="154" height="132" rx="10" fill="#eef2f6" stroke="#60788f" stroke-width="2"/><path d="M20 32h114v82H20z" fill="#d9e1e8" stroke="#60788f" stroke-width="2"/><rect x="32" y="44" width="30" height="58" rx="3" fill="#fff" stroke="#60788f"/><rect x="72" y="44" width="30" height="58" rx="3" fill="#fff" stroke="#60788f"/><rect x="112" y="44" width="12" height="58" rx="2" fill="#fff" stroke="#60788f"/><g fill="#5b9bd5"><circle cx="40" cy="53" r="2"/><circle cx="80" cy="53" r="2"/><circle cx="118" cy="53" r="2"/></g><path d="M10 32L77 5l67 27" fill="none" stroke="#60788f" stroke-width="4"/><text x="77" y="126" text-anchor="middle" font-family="Segoe UI,Arial" font-size="12" fill="#40566b">On-prem servers</text></g>'''
def layout(m):
 n=max(1,len(m['spokes'])); sh=270; gap=42; top=130; H=max(980,top+n*(sh+gap)+175)
 return {'w':1840,'h':H,'onprem':(45,260,280,390),'er':(365,410),'hub':(520,145,610,max(650,n*(sh+gap)-20)),'spokes':[(1260,top+i*(sh+gap),520,sh) for i in range(n)]}
def svg(m):
 L=layout(m);W,H=L['w'],L['h'];hx,hy,hw,hh=L['hub'];ox,oy,ow,oh=L['onprem'];ex,ey=L['er']
 def t(x,y,s,z=18,w=400,a='start',f='#17324d'):return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial" font-size="{z}" font-weight="{w}" text-anchor="{a}" fill="{f}">{esc(s)}</text>'
 def b(x,y,w,h,s,f,rx=18,sw=2):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" stroke="{s}" stroke-width="{sw}"/>'
 defs='<defs><marker id="end" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker><marker id="start" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M10 0L0 5L10 10z" fill="#0078d4"/></marker></defs>'
 A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs}<rect width="100%" height="100%" fill="white"/>',t(45,58,m['title'],36,700),t(45,91,m['subtitle'],18,400,f='#5d7185'),b(ox,oy,ow,oh,'#8292a2','#f6f8fa'),t(ox+ow/2,oy+45,'On-Premises Datacentre',20,700,'middle'),datacentre(ox+63,oy+90),t(ox+ow/2,oy+330,'Corporate Network',16,700,'middle'),t(ox+ow/2,oy+356,'CIDR not specified',14,400,'middle','#718295'),icon('expressroute',ex,ey),t(ex+38,ey+102,'ExpressRoute Circuit',16,700,'middle'),f'<path d="M{ox+ow} {ey+38}H{ex-8}" stroke="#0078d4" stroke-width="4" marker-end="url(#end)"/>',b(hx,hy,hw,hh,'#0078d4','#f4faff',20,3),t(hx+30,hy+43,'Hub Virtual Network',27,700),t(hx+30,hy+75,f"{m['hub']['name']} • {m['hub']['cidr'] or 'CIDR not specified'}",17,400,f='#526a80'),b(hx+55,hy+125,hw-110,205,'#75b9e7','#fff',14),t(hx+80,hy+158,'GatewaySubnet',18,700),t(hx+80,hy+184,'CIDR not specified',14,400,f='#718295'),icon('gateway',hx+267,hy+205,82,82),t(hx+308,hy+310,'ExpressRoute Gateway',18,700,'middle'),b(hx+55,hy+370,hw-110,205,'#75b9e7','#fff',14),t(hx+80,hy+403,'AzureFirewallSubnet',18,700),t(hx+80,hy+429,'CIDR not specified',14,400,f='#718295'),icon('firewall',hx+267,hy+448,82,82),t(hx+308,hy+553,'Azure Firewall',18,700,'middle'),f'<path d="M{ex+84} {ey+38}H{hx+25}V{hy+228}H{hx+55}" fill="none" stroke="#0078d4" stroke-width="4" marker-end="url(#end)"/>',t(405,ey-18,'Private ExpressRoute connectivity',13,600,'middle','#526a80')]
 for i,(sp,(x,y,w,h)) in enumerate(zip(m['spokes'],L['spokes']),1):
  cy=y+h/2; huby=hy+210+i*92; mid=(hx+hw+x)//2
  A += [f'<path d="M{hx+hw} {huby}H{mid}V{cy}H{x}" fill="none" stroke="#0078d4" stroke-width="4" marker-start="url(#start)" marker-end="url(#end)"/>',t(mid+8,cy-12,f'VNet Peering {i}',14,700,'middle','#526a80'),b(x,y,w,h,'#39a869','#f5fff8',18,3),t(x+28,y+40,f'Spoke Virtual Network {i:02d}',22,700),t(x+28,y+69,f"{sp['name']} • {sp['cidr'] or 'CIDR not specified'}",16,400,f='#526a80'),b(x+35,y+95,w-70,138,'#8dc9ed','#fff',12),t(x+58,y+128,'Workload Subnet',16,700),t(x+58,y+153,sp['subnet'] or 'CIDR not specified',14,400,f='#718295'),icon('vm',x+w-150,y+122,78,78),t(x+w-112,y+220,f"{sp['vm']} • Windows Server",14,700,'middle')]
 A += [t(45,H-82,'Unspecified CIDRs are deliberately not invented.',15),t(45,H-54,'Gateway transit, remote gateway and forwarded traffic are peering policy.',15),t(45,H-26,'Add UDRs when spoke traffic must be forced through Azure Firewall.',15),'</svg>'];return ''.join(A)
def drawio(m):
 L=layout(m);hx,hy,hw,hh=L['hub'];ox,oy,ow,oh=L['onprem'];ex,ey=L['er']
 def c(i,v,x,y,w,h,style,parent='1'):return f'<mxCell id="{i}" value="{html.escape(v)}" style="{style}" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
 R=['<mxCell id="0"/><mxCell id="1" parent="0"/>',c('op','On-Premises Datacentre&#xa;Corporate Network',ox,oy,ow,oh,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f6f8fa;strokeColor=#8292a2;'),c('er','ExpressRoute Circuit',ex,ey,84,84,'ellipse;html=1;fillColor=#0078d4;fontColor=#ffffff;'),c('hub',f"Hub Virtual Network&#xa;{m['hub']['name']} • {m['hub']['cidr'] or 'CIDR not specified'}",hx,hy,hw,hh,'swimlane;rounded=1;html=1;startSize=80;container=1;strokeColor=#0078d4;fillColor=#f4faff;'),c('gw','GatewaySubnet&#xa;ExpressRoute Gateway',55,125,500,205,'rounded=1;html=1;strokeColor=#75b9e7;fillColor=#ffffff;','hub'),c('fw','AzureFirewallSubnet&#xa;Azure Firewall',55,370,500,205,'rounded=1;html=1;strokeColor=#75b9e7;fillColor=#ffffff;','hub')]
 for i,(sp,(x,y,w,h)) in enumerate(zip(m['spokes'],L['spokes']),1):R += [c(f's{i}',f"Spoke Virtual Network {i:02d}&#xa;{sp['name']} • {sp['cidr'] or 'CIDR not specified'}",x,y,w,h,'swimlane;rounded=1;html=1;startSize=75;container=1;strokeColor=#39a869;fillColor=#f5fff8;'),c(f'vm{i}',f"Workload Subnet • {sp['subnet'] or 'CIDR not specified'}&#xa;{sp['vm']} • Windows Server",35,95,w-70,138,'rounded=1;html=1;strokeColor=#8dc9ed;fillColor=#ffffff;',f's{i}')]
 edges=[('e1','op','er','ExpressRoute'),('e2','er','gw','Private connectivity')]+[(f'ep{i}','hub',f's{i}',f'VNet Peering {i}') for i in range(1,len(m['spokes'])+1)]
 for eid,s,d,l in edges:R.append(f'<mxCell id="{eid}" value="{l}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#0078d4;strokeWidth=3;startArrow={"block" if eid.startswith("ep") else "none"};endArrow=block;jettySize=auto;orthogonalLoop=1;" edge="1" parent="1" source="{s}" target="{d}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="V5 Azure Architecture"><mxGraphModel page="1" pageWidth="1840" pageHeight="'+str(L['h'])+'"><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
PAGE='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Studio V5</title><style>body{margin:0;font-family:Arial;background:#07111f;color:#eef5ff}.top{padding:16px 22px;background:#0c1a2d;font-weight:800;font-size:20px}.top b{color:#39a8ff}.grid{display:grid;grid-template-columns:380px minmax(0,1fr);min-height:calc(100vh - 58px)}.side{padding:18px;background:#0c1a2d}.main{padding:18px;min-width:0}.card{background:#11243b;border:1px solid #29415e;border-radius:14px;padding:15px}textarea{width:100%;height:390px;box-sizing:border-box;background:#071522;color:white;border:1px solid #395675;border-radius:10px;padding:12px}.btn{display:inline-block;margin:10px 5px 0 0;background:#1688f8;color:white;border:0;border-radius:9px;padding:11px 15px;font-weight:700;text-decoration:none}.secondary{background:#29415e}.canvas{background:white;border-radius:14px;overflow:auto;max-height:82vh}.canvas img{display:block;width:100%;height:auto;max-width:1840px}@media(max-width:850px){.grid{display:block}.side,.main{padding:10px}.canvas{height:auto;max-height:none;overflow:auto}.canvas img{width:145%;max-width:none;height:auto}.top{font-size:17px;padding:13px 14px}textarea{height:300px}}</style></head><body><div class="top"><b>Azure</b> Architecture Studio <small>V5</small></div><div class="grid"><div class="side"><div class="card"><form method="post"><h3>Architecture requirement</h3><textarea name="req">{{req}}</textarea><button class="btn">Generate V5 Architecture</button></form>{% if has %}<a class="btn secondary" href="/v5.svg" download>SVG</a><a class="btn secondary" href="/v5.drawio" download>Draw.io</a><a class="btn secondary" href="/v5/model" download>JSON</a>{% endif %}</div></div><div class="main"><div class="canvas">{% if has %}<img src="/v5.svg?t={{stamp}}" alt="Azure architecture diagram">{% else %}<div style="color:#456;padding:30px">Enter a requirement and generate the V5 architecture.</div>{% endif %}</div></div></div></body></html>'''
@app.route('/',methods=['GET','POST'])
def home():
 global CURRENT
 req=request.form.get('req','') if request.method=='POST' else (CURRENT['source'] if CURRENT else '')
 if request.method=='POST' and req.strip():CURRENT=parse_requirement(req)
 return render_template_string(PAGE,req=req,has=CURRENT is not None,stamp=int(time.time()))
@app.route('/v5.svg')
def rsvg():return Response(svg(CURRENT),mimetype='image/svg+xml',headers={'Content-Disposition':'inline; filename=architecture-v5.svg'}) if CURRENT else Response('No diagram',404)
@app.route('/v5.drawio')
def rdraw():return Response(drawio(CURRENT),mimetype='application/xml',headers={'Content-Disposition':'attachment; filename=architecture-v5.drawio'}) if CURRENT else Response('No diagram',404)
@app.route('/v5/model')
def rmodel():return Response(json.dumps(CURRENT,indent=2),mimetype='application/json') if CURRENT else Response('{}',404)
@app.route('/health')
def health():return {'ok':True,'version':'v5','renderer':'official-icons-datacentre-orthogonal-peering'}
if __name__=='__main__':app.run(host='0.0.0.0',port=3000)
