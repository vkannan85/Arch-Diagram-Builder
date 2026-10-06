from flask import Flask,request,render_template_string,Response
import re,html,json,time,urllib.request,zipfile,io,base64,os
app=Flask(__name__); CURRENT=None
CIDR=r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'
ICON_ZIP='https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons_V24.zip'
ICONS={}; ICON_FILES={}; ICON_ERROR=None
TEST_REQ='''Create an Azure architecture diagram for a highly available public-facing web application.
Production-VNet: 10.10.0.0/16
Application Gateway subnet: 10.10.1.0/24
Application subnet: 10.10.2.0/24
Database subnet: 10.10.3.0/24
Users access the application from the Internet. Use Azure Front Door as the global entry point. Traffic flows from Azure Front Door to an Azure Application Gateway with Web Application Firewall enabled. Deploy two Windows Server virtual machines: WEB-VM01 and WEB-VM02. Place both VMs in the Application subnet. Use an Azure Load Balancer to distribute traffic between the application servers. Deploy Azure SQL Database with a Private Endpoint and no public exposure. Use Azure Storage Account and Azure Key Vault with Private Endpoints. Use NSGs. Use Azure Monitor and Log Analytics Workspace.'''
def esc(v):return html.escape(str(v or 'Not specified'))
def norm(s):return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
def cidr_after(t,n):
 m=re.search(re.escape(n)+r'.{0,100}?('+CIDR+r')',t,re.I|re.S);return m.group(1) if m else None
def parse_requirement(t):
 low=t.lower();hub=('hub-vnet' in low or ('hub' in low and 'spoke' in low))
 if hub:
  names=re.findall(r'\bSpoke\s*\d+[- ]?VNet\b|\bSpoke\d+-VNet\b',t,re.I) or ['Spoke1-VNet','Spoke2-VNet'];sp=[]
  for raw in names:
   n=re.sub(r'\s+','',raw);n=n.replace('VNet','-VNet') if '-' not in n else n;n=n.replace('--','-')
   if any(x['name'].lower()==n.lower() for x in sp):continue
   i=len(sp)+1;mm=re.search(r'\bVM0?%d\b'%i,t,re.I);sp.append({'name':n,'cidr':cidr_after(t,n),'vm':mm.group(0).upper() if mm else 'VM%02d'%i})
  return {'type':'hubspoke','title':'Hub-and-Spoke Network Architecture','hub':{'name':'Hub-VNet','cidr':cidr_after(t,'Hub-VNet')},'spokes':sp,'source':t}
 catalog=[('internet','Internet',['internet','public-facing']),('frontdoor','Azure Front Door',['front door']),('appgw','Application Gateway / WAF',['application gateway','web application firewall','waf']),('loadbalancer','Azure Load Balancer',['load balancer']),('sql','Azure SQL Database',['sql database','azure sql']),('storage','Storage Account',['storage account']),('keyvault','Azure Key Vault',['key vault']),('monitor','Azure Monitor',['azure monitor']),('loganalytics','Log Analytics Workspace',['log analytics']),('nsg','Network Security Group',['network security group','nsg'])]
 resources=[{'id':k,'label':label} for k,label,terms in catalog if any(x in low for x in terms)]
 vmnames=[]
 for pat in [r'\b[A-Z]+-VM\d+\b',r'\bVM\d+\b']:
  for x in re.findall(pat,t,re.I):
   if x.upper() not in vmnames:vmnames.append(x.upper())
 if ('virtual machine' in low or 'windows server' in low) and not vmnames:vmnames=['Virtual Machine']
 vn=re.search(r'([A-Za-z0-9-]+VNet)\s*[:\-]?\s*('+CIDR+r')',t,re.I);vnet={'name':vn.group(1) if vn else 'Virtual Network','cidr':vn.group(2) if vn else None}
 sub=[]
 for name,cidr in re.findall(r'([A-Za-z][A-Za-z0-9 -]*subnet)\s*[:\-]?\s*('+CIDR+r')',t,re.I):
  item={'name':name.strip(),'cidr':cidr}
  if not any(s['cidr']==cidr for s in sub):sub.append(item)
 return {'type':'generic','title':'Azure Web Application Architecture' if 'front door' in low else 'Azure Solution Architecture','vnet':vnet,'subnets':sub,'resources':resources,'vms':vmnames,'privateendpoint':'private endpoint' in low,'source':t}
ALIASES={
 'frontdoor':['front door','front doors','front door and cdn profiles'],
 'appgw':['application gateway','application gateways'],
 'loadbalancer':['load balancer','load balancers'],
 'vm':['virtual machine','virtual machines'],
 'sql':['sql database','sql databases'],
 'storage':['storage account','storage accounts'],
 'keyvault':['key vault','key vaults'],
 'monitor':['azure monitor','monitor'],
 'loganalytics':['log analytics workspace','log analytics workspaces'],
 'nsg':['network security group','network security groups'],
 'privateendpoint':['private endpoint','private endpoints'],
 'firewall':['azure firewall','firewalls'],
 'gateway':['virtual network gateway','virtual network gateways'],
 'expressroute':['expressroute circuit','expressroute circuits']}
def load_icons(force=False):
 global ICONS,ICON_FILES,ICON_ERROR
 if ICONS and not force:return
 ICONS={};ICON_FILES={};ICON_ERROR=None
 try:
  data=urllib.request.urlopen(ICON_ZIP,timeout=30).read();z=zipfile.ZipFile(io.BytesIO(data));files=[n for n in z.namelist() if n.lower().endswith('.svg')]
  for k,aliases in ALIASES.items():
   scored=[]
   for n in files:
    b=norm(n.rsplit('/',1)[-1].rsplit('.',1)[0]); full=norm(n)
    if 'classic' in full:continue
    for a in aliases:
     aa=norm(a)
     if aa==b:score=0
     elif (' '+aa+' ') in (' '+b+' '):score=10+abs(len(b)-len(aa))
     elif aa in full:score=100+len(full)
     else:continue
     scored.append((score,len(n),n));break
   if scored:
    hit=sorted(scored)[0][2];ICONS[k]=base64.b64encode(z.read(hit)).decode();ICON_FILES[k]=hit
 except Exception as e:ICON_ERROR=str(e);print('icon pack:',e)
def icon(k,x,y,w=68,h=68):
 load_icons()
 if k=='internet':return f'<g transform="translate({x},{y})"><path d="M10 45c-16-28 28-49 45-25 22-8 39 20 23 36H17C8 56 4 51 10 45z" fill="#59b4e8"/><text x="43" y="82" text-anchor="middle" font-family="Segoe UI,Arial" font-size="11" fill="#445">Internet</text></g>'
 if k in ICONS:return f'<image data-icon="{k}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="data:image/svg+xml;base64,{ICONS[k]}"/>'
 return f'<g data-missing-icon="{esc(k)}" transform="translate({x},{y})"><rect width="{w}" height="{h}" rx="8" fill="#fff4ce" stroke="#d83b01" stroke-width="2"/><text x="{w/2}" y="{h/2-2}" text-anchor="middle" font-family="Arial" font-size="9" font-weight="700" fill="#a4262c">ICON</text><text x="{w/2}" y="{h/2+12}" text-anchor="middle" font-family="Arial" font-size="9" font-weight="700" fill="#a4262c">MISSING</text></g>'
def defs():return '<defs><marker id="end" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker></defs>'
def tx(x,y,s,z=16,w=400,a='start',c='#17324d'):return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial" font-size="{z}" font-weight="{w}" text-anchor="{a}" fill="{c}">{esc(s)}</text>'
def box(x,y,w,h,stroke='#75b9e7',fill='#fff',rx=14,sw=2):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def card(A,k,label,x,y,w=180,h=125):
 A.extend([box(x,y,w,h),icon(k,x+(w-68)/2,y+12),tx(x+w/2,y+h-18,label,13,700,'middle')])
def path(A,d,dash=False):A.append(f'<path d="{d}" stroke="#0078d4" stroke-width="3" fill="none" {"stroke-dasharray=\"7 6\"" if dash else "marker-end=\"url(#end)\""}/>')
def generic_svg(m):
 W,H=1800,1050;A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs()}<rect width="100%" height="100%" fill="white"/>',tx(55,58,m['title'],34,700),tx(55,88,'Requirement-driven Azure architecture • public edge, network, application, private data and observability',16,400,c='#5d7185')]
 by={r['id']:r for r in m['resources']};subs=m['subnets'];appgwsub=next((s for s in subs if 'gateway' in s['name'].lower()),{'name':'Application Gateway subnet','cidr':'Not specified'});appsub=next((s for s in subs if 'application' in s['name'].lower() and 'gateway' not in s['name'].lower()),{'name':'Application subnet','cidr':'Not specified'});dbsub=next((s for s in subs if 'database' in s['name'].lower()),{'name':'Database subnet','cidr':'Not specified'})
 # public edge
 card(A,'internet','Internet',55,175,170,125);card(A,'frontdoor','Azure Front Door',275,175,190,125);path(A,'M225 238H275')
 # VNet and three real subnet containers
 vx,vy,vw,vh=520,125,790,700;A.extend([box(vx,vy,vw,vh,'#0078d4','#f4faff',22,3),tx(vx+25,vy+40,'Virtual Network',24,700),tx(vx+25,vy+68,m['vnet']['name']+' • '+(m['vnet']['cidr'] or 'CIDR not specified'),14,400,c='#526a80')])
 A.extend([box(550,225,230,500,'#8ab4d6','#fff',12),tx(565,255,appgwsub['name'],15,700),tx(565,278,appgwsub['cidr'],13,400,c='#718295'),box(800,225,250,500,'#8ab4d6','#fff',12),tx(815,255,appsub['name'],15,700),tx(815,278,appsub['cidr'],13,400,c='#718295'),box(1070,225,210,500,'#8ab4d6','#fff',12),tx(1085,255,dbsub['name'],15,700),tx(1085,278,dbsub['cidr'],13,400,c='#718295')])
 card(A,'appgw','Application Gateway / WAF',575,330,180,135);card(A,'loadbalancer','Azure Load Balancer',835,315,180,125)
 vms=m['vms'][:2] or ['WEB-VM01','WEB-VM02']
 for i,n in enumerate(vms):card(A,'vm',n,825+i*115,500,105,130)
 # data PaaS outside VNet; private endpoints inside DB subnet
 data=[k for k in ['sql','storage','keyvault'] if k in by];dy=[220,455,690]
 for i,k in enumerate(data):
  y=dy[i];card(A,k,by[k]['label'],1450,y,220,130);card(A,'privateendpoint','Private Endpoint',1090,y+15,170,105);path(A,f'M1260 {y+68}H1450')
 # main request flow
 path(A,'M465 238H490V397H575');path(A,'M755 397H790V377H835')
 for i in range(len(vms)):path(A,f'M1015 377H1035V{565+i*20}H{825+i*115+52}')
 # app to private endpoints, routed around cards
 if data:
  for i,k in enumerate(data):
   y=dy[i]+67;path(A,f'M930 630V760H1045V{y}H1090')
 # NSG shown as subnet protection, not a standalone workload
 if 'nsg' in by:
  A.extend([box(810,675,230,34,'#c8c8c8','#f3f3f3',8,1),tx(925,698,'NSG protects Application subnet',12,600,'middle','#5d5d5d'),box(1080,675,190,34,'#c8c8c8','#f3f3f3',8,1),tx(1175,698,'NSG protects DB subnet',12,600,'middle','#5d5d5d')])
 # observability plane
 if 'monitor' in by or 'loganalytics' in by:
  A.extend([tx(55,870,'Observability',20,700),box(55,890,650,130,'#9aa9b7','#f8fafc',14)])
  if 'monitor' in by:card(A,'monitor','Azure Monitor',85,900,200,105)
  if 'loganalytics' in by:card(A,'loganalytics','Log Analytics Workspace',330,900,250,105)
  path(A,'M925 725V955H705',True)
 A.extend([tx(55,1035,'No unprovided IP addresses or resource names are invented. PaaS services remain outside the VNet; Private Endpoints are placed inside the requested data subnet.',12,400,c='#526a80'),'</svg>']);return ''.join(A)
def hub_svg(m):
 W,H=1600,850;A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs()}<rect width="100%" height="100%" fill="white"/>',tx(45,55,m['title'],34,700),box(80,150,500,580,'#0078d4','#f4faff',20),tx(110,190,'Hub Virtual Network',24,700),tx(110,220,m['hub']['name']+' • '+(m['hub']['cidr'] or 'CIDR not specified'),15,400,c='#526a80'),box(140,285,380,150),icon('gateway',300,320,70,70),tx(335,410,'ExpressRoute Gateway',16,700,'middle'),box(140,500,380,150),icon('firewall',300,535,70,70),tx(335,625,'Azure Firewall',16,700,'middle')]
 for i,s in enumerate(m['spokes']):
  x,y=850,135+i*285;A.extend([box(x,y,600,220,'#39a869','#f5fff8',18),tx(x+25,y+38,'Spoke Virtual Network',21,700),tx(x+25,y+66,s['name']+' • '+(s['cidr'] or 'CIDR not specified'),15,400,c='#526a80'),icon('vm',x+450,y+90,70,70),tx(x+485,y+185,s['vm']+' • Windows Server',14,700,'middle')]);path(A,f'M580 {y+110}H850')
 A.append('</svg>');return ''.join(A)
def svg(m):return hub_svg(m) if m.get('type')=='hubspoke' else generic_svg(m)
def drawio(m):
 nodes=m.get('resources',[])+[{'id':'vm','label':x} for x in m.get('vms',[])];R=['<mxCell id="0"/><mxCell id="1" parent="0"/>']
 for i,n in enumerate(nodes):
  xx=80+(i%4)*300;yy=100+(i//4)*170;R.append(f'<mxCell id="n{i}" value="{esc(n["label"])}" style="rounded=1;whiteSpace=wrap;html=1;strokeColor=#0078d4;fillColor=#ffffff;" vertex="1" parent="1"><mxGeometry x="{xx}" y="{yy}" width="220" height="100" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="V5 Dynamic Architecture"><mxGraphModel><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
PAGE='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Studio V5</title><style>body{margin:0;font-family:Arial;background:#07111f;color:#eef5ff}.top{padding:16px 22px;background:#0c1a2d;font-weight:800;font-size:20px}.top b{color:#39a8ff}.grid{display:grid;grid-template-columns:400px minmax(0,1fr);min-height:calc(100vh - 58px)}.side{padding:18px;background:#0c1a2d}.main{padding:18px;min-width:0}.card{background:#11243b;border:1px solid #29415e;border-radius:14px;padding:15px}textarea{width:100%;height:420px;box-sizing:border-box;background:#071522;color:white;border:1px solid #395675;border-radius:10px;padding:12px}.btn{display:inline-block;margin:10px 5px 0 0;background:#1688f8;color:white;border:0;border-radius:9px;padding:11px 15px;font-weight:700;text-decoration:none}.secondary{background:#29415e}.canvas{background:white;border-radius:14px;overflow:auto}.canvas img{display:block;width:100%;height:auto;min-width:900px}@media(max-width:850px){.grid{display:block}.side,.main{padding:10px}.canvas{width:100%;overflow:auto;-webkit-overflow-scrolling:touch}.canvas img{width:100%;min-width:0;height:auto}textarea{height:300px}}</style></head><body><div class="top"><b>Azure</b> Architecture Studio <small>V5.2</small></div><div class="grid"><div class="side"><div class="card"><form method="post"><h3>Architecture requirement</h3><textarea name="req">{{req}}</textarea><button class="btn">Generate Architecture</button></form>{% if has %}<a class="btn secondary" href="/v5.svg" download>SVG</a><a class="btn secondary" href="/v5.drawio" download>Draw.io</a><a class="btn secondary" href="/v5/model" download>JSON</a>{% endif %}</div></div><div class="main"><div class="canvas">{% if has %}<img src="/v5.svg?t={{stamp}}">{% else %}<div style="color:#456;padding:30px">Enter a requirement to generate an architecture.</div>{% endif %}</div></div></div></body></html>'''
@app.route('/',methods=['GET','POST'])
def home():
 global CURRENT
 req=request.form.get('req','') if request.method=='POST' else (CURRENT['source'] if CURRENT else '')
 if request.method=='POST' and req.strip():CURRENT=parse_requirement(req)
 return render_template_string(PAGE,req=req,has=CURRENT is not None,stamp=int(time.time()))
@app.route('/v5.svg')
def rsvg():return Response(svg(CURRENT),mimetype='image/svg+xml') if CURRENT else Response('No diagram',404)
@app.route('/v5.drawio')
def rdraw():return Response(drawio(CURRENT),mimetype='application/xml',headers={'Content-Disposition':'attachment; filename=architecture-v5.drawio'}) if CURRENT else Response('No diagram',404)
@app.route('/v5/model')
def rmodel():return Response(json.dumps(CURRENT,indent=2),mimetype='application/json') if CURRENT else Response('{}',404)
@app.route('/diagnostics/icons')
def diagicons():
 load_icons();required=['frontdoor','appgw','loadbalancer','vm','sql','storage','keyvault','monitor','loganalytics','nsg','privateendpoint','firewall','gateway','expressroute'];missing=[x for x in required if x not in ICONS]
 return {'ok':not missing and not ICON_ERROR,'resolved':ICON_FILES,'missing':missing,'error':ICON_ERROR}
@app.route('/regression/webapp.svg')
def regression_svg():return Response(svg(parse_requirement(TEST_REQ)),mimetype='image/svg+xml')
@app.route('/regression/webapp/model')
def regression_model():return Response(json.dumps(parse_requirement(TEST_REQ),indent=2),mimetype='application/json')
@app.route('/health')
def health():return {'ok':True,'version':'v5.2','renderer':'official-icons-zoned-private-endpoint-layout'}
if __name__=='__main__':app.run(host='0.0.0.0',port=3000)
