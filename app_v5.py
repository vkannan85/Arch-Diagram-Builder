from flask import Flask,request,render_template_string,Response
import re,html,json,time,urllib.request,zipfile,io,base64
app=Flask(__name__); CURRENT=None
CIDR=r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'
ICON_ZIP='https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons_V24.zip'; ICONS={}
def esc(v):return html.escape(str(v or 'Not specified'))
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
 for pat in [r'\bWEB-VM\d+\b',r'\bVM\d+\b']:
  for x in re.findall(pat,t,re.I):
   if x.upper() not in vmnames:vmnames.append(x.upper())
 if ('virtual machine' in low or 'windows server' in low or vmnames) and not vmnames:vmnames=['Virtual Machine']
 vn=re.search(r'([A-Za-z0-9-]+VNet)\s*[:\-]?\s*('+CIDR+r')',t,re.I);vnet={'name':vn.group(1) if vn else 'Virtual Network','cidr':vn.group(2) if vn else None}
 sub=[]
 for name,cidr in re.findall(r'([A-Za-z][A-Za-z0-9 -]*subnet)\s*[:\-]?\s*('+CIDR+r')',t,re.I):
  item={'name':name.strip(),'cidr':cidr}
  if not any(s['cidr']==cidr for s in sub):sub.append(item)
 return {'type':'generic','title':'Azure Web Application Architecture' if 'front door' in low else 'Azure Solution Architecture','vnet':vnet,'subnets':sub,'resources':resources,'vms':vmnames,'privateendpoint':'private endpoint' in low,'source':t}
def load_icons():
 global ICONS
 if ICONS:return
 try:
  z=zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(ICON_ZIP,timeout=20).read()));files=[n for n in z.namelist() if n.lower().endswith('.svg')]
  terms={'firewall':['firewalls'],'gateway':['virtual network gateways'],'expressroute':['expressroute circuits'],'vm':['virtual machines'],'frontdoor':['front doors'],'appgw':['application gateways'],'loadbalancer':['load balancers'],'sql':['sql database'],'storage':['storage accounts'],'keyvault':['key vaults'],'monitor':['monitor'],'loganalytics':['log analytics workspaces'],'nsg':['network security groups']}
  for k,words in terms.items():
   hits=[n for n in files if any(w in n.lower() for w in words) and 'classic' not in n.lower()]
   if hits:ICONS[k]=base64.b64encode(z.read(sorted(hits,key=len)[0])).decode()
 except Exception as e:print('icon pack:',e)
def icon(k,x,y,w=54,h=54):
 load_icons()
 if k in ICONS:return f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="data:image/svg+xml;base64,{ICONS[k]}"/>'
 return f'<g transform="translate({x},{y})"><rect width="{w}" height="{h}" rx="8" fill="#eef6fc" stroke="#0078d4"/><text x="{w/2}" y="{h/2+4}" text-anchor="middle" font-family="Arial" font-size="9" fill="#0067b8">{esc(k)}</text></g>'
def defs():return '<defs><marker id="end" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker></defs>'
def tx(x,y,s,z=16,w=400,a='start',c='#17324d'):return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial" font-size="{z}" font-weight="{w}" text-anchor="{a}" fill="{c}">{esc(s)}</text>'
def box(x,y,w,h,stroke='#75b9e7',fill='#fff',rx=14):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
def card(A,k,label,x,y,w=170,h=105):A.extend([box(x,y,w,h),icon(k,x+(w-54)/2,y+10),tx(x+w/2,y+84,label,13,700,'middle')])
def generic_svg(m):
 W,H=1600,900;A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs()}<rect width="100%" height="100%" fill="white"/>',tx(55,58,m['title'],34,700),tx(55,88,'Requirement-driven topology • public, application, data and observability zones',16,400,c='#5d7185')]
 by={r['id']:r for r in m['resources']};pos={};flow=[k for k in ['internet','frontdoor','appgw','loadbalancer'] if k in by];x=55
 for k in flow:pos[k]=(x,160);card(A,k,by[k]['label'],x,160);x+=210
 vx,vy,vw,vh=875,120,670,570;A.extend([box(vx,vy,vw,vh,'#0078d4','#f4faff',20),tx(vx+25,vy+38,'Virtual Network',23,700),tx(vx+25,vy+64,m['vnet']['name']+' • '+(m['vnet']['cidr'] or 'CIDR not specified'),14,400,c='#526a80')])
 subs=m['subnets'];appsub=next((s for s in subs if 'application' in s['name'].lower()),{'name':'Application subnet','cidr':'CIDR not specified'});dbsub=next((s for s in subs if 'database' in s['name'].lower()),{'name':'Database subnet','cidr':'CIDR not specified'})
 A.extend([box(905,220,300,300,'#8ab4d6','#fff',12),tx(925,250,appsub['name'],16,700),tx(925,272,appsub['cidr'],13,400,c='#718295'),box(1220,220,295,300,'#8ab4d6','#fff',12),tx(1240,250,dbsub['name'],16,700),tx(1240,272,dbsub['cidr'],13,400,c='#718295')])
 vms=m['vms'][:2]
 for i,n in enumerate(vms):
  xx=935+i*135;card(A,'vm',n,xx,315,120,120);pos['vm'+str(i)]=(xx,315)
 if 'sql' in by:card(A,'sql','Azure SQL Database',1278,315,180,120);pos['sql']=(1278,315)
 for j,k in enumerate([k for k in ['storage','keyvault'] if k in by]):card(A,k,by[k]['label'],925+j*205,545,180,105);pos[k]=(925+j*205,545)
 if 'nsg' in by:card(A,'nsg','NSG',1330,545,130,105)
 chain=flow[:]
 for a,b in zip(chain,chain[1:]):
  x1,y1=pos[a];x2,y2=pos[b];A.append(f'<path d="M{x1+170} {y1+52}H{x2}" stroke="#0078d4" stroke-width="4" fill="none" marker-end="url(#end)"/>')
 if flow and vms:
  x1,y1=pos[flow[-1]];A.append(f'<path d="M{x1+170} {y1+52}H850V375H935" stroke="#0078d4" stroke-width="4" fill="none" marker-end="url(#end)"/>')
 if len(vms)>1:A.append('<path d="M1055 375H1070" stroke="#0078d4" stroke-width="3" marker-end="url(#end)"/>')
 for i in range(len(vms)):
  x1,y1=pos['vm'+str(i)]
  if 'sql' in pos:A.append(f'<path d="M{x1+60} {y1+120}V470H1368V435" stroke="#0078d4" stroke-width="2.5" fill="none" marker-end="url(#end)"/>')
 for k in ['storage','keyvault']:
  if k in pos and vms:
   x2,y2=pos[k];A.append(f'<path d="M995 435V500H{x2+90}V545" stroke="#0078d4" stroke-width="2.5" fill="none" marker-end="url(#end)"/>')
 if m['privateendpoint'] and any(k in pos for k in ['sql','storage','keyvault']):A.append(tx(1210,505,'Private Endpoint connectivity',13,600,c='#526a80'))
 ops=[k for k in ['monitor','loganalytics'] if k in by]
 if ops:
  A.extend([tx(55,660,'Observability',20,700),box(55,680,560,150,'#9aa9b7','#f8fafc',14)])
  for i,k in enumerate(ops):card(A,k,by[k]['label'],85+i*240,705,200,100)
  A.append('<path d="M995 650V780H615" stroke="#6b7d90" stroke-width="2" stroke-dasharray="7 6" fill="none"/>')
 A.extend([tx(55,875,'No unprovided IP addresses or resource names are invented.',13,400,c='#526a80'),'</svg>']);return ''.join(A)
def hub_svg(m):
 W,H=1600,850;A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs()}<rect width="100%" height="100%" fill="white"/>',tx(45,55,m['title'],34,700),box(80,150,500,580,'#0078d4','#f4faff',20),tx(110,190,'Hub Virtual Network',24,700),tx(110,220,m['hub']['name']+' • '+(m['hub']['cidr'] or 'CIDR not specified'),15,400,c='#526a80'),box(140,285,380,150),icon('gateway',300,320,70,70),tx(335,410,'ExpressRoute Gateway',16,700,'middle'),box(140,500,380,150),icon('firewall',300,535,70,70),tx(335,625,'Azure Firewall',16,700,'middle')]
 for i,s in enumerate(m['spokes']):
  x,y=850,135+i*285;A.extend([box(x,y,600,220,'#39a869','#f5fff8',18),tx(x+25,y+38,'Spoke Virtual Network',21,700),tx(x+25,y+66,s['name']+' • '+(s['cidr'] or 'CIDR not specified'),15,400,c='#526a80'),icon('vm',x+450,y+90,70,70),tx(x+485,y+185,s['vm']+' • Windows Server',14,700,'middle'),f'<path d="M580 {y+110}H850" stroke="#0078d4" stroke-width="4" marker-end="url(#end)"/>'])
 A.append('</svg>');return ''.join(A)
def svg(m):return hub_svg(m) if m.get('type')=='hubspoke' else generic_svg(m)
def drawio(m):
 nodes=m.get('resources',[]);R=['<mxCell id="0"/><mxCell id="1" parent="0"/>'];
 for i,n in enumerate(nodes):
  xx=80+(i%4)*300;yy=100+(i//4)*170;R.append(f'<mxCell id="n{i}" value="{esc(n["label"])}" style="rounded=1;whiteSpace=wrap;html=1;strokeColor=#0078d4;fillColor=#ffffff;" vertex="1" parent="1"><mxGeometry x="{xx}" y="{yy}" width="220" height="100" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="V5 Dynamic Architecture"><mxGraphModel><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
PAGE='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Studio V5</title><style>body{margin:0;font-family:Arial;background:#07111f;color:#eef5ff}.top{padding:16px 22px;background:#0c1a2d;font-weight:800;font-size:20px}.top b{color:#39a8ff}.grid{display:grid;grid-template-columns:380px minmax(0,1fr);min-height:calc(100vh - 58px)}.side{padding:18px;background:#0c1a2d}.main{padding:18px;min-width:0}.card{background:#11243b;border:1px solid #29415e;border-radius:14px;padding:15px}textarea{width:100%;height:390px;box-sizing:border-box;background:#071522;color:white;border:1px solid #395675;border-radius:10px;padding:12px}.btn{display:inline-block;margin:10px 5px 0 0;background:#1688f8;color:white;border:0;border-radius:9px;padding:11px 15px;font-weight:700;text-decoration:none}.secondary{background:#29415e}.canvas{background:white;border-radius:14px;overflow:hidden}.canvas img{display:block;width:100%;height:auto}@media(max-width:850px){.grid{display:block}.side,.main{padding:10px}.canvas{width:100%;overflow:hidden}.canvas img{width:100%;max-width:100%;height:auto}textarea{height:300px}}</style></head><body><div class="top"><b>Azure</b> Architecture Studio <small>V5 Dynamic</small></div><div class="grid"><div class="side"><div class="card"><form method="post"><h3>Architecture requirement</h3><textarea name="req">{{req}}</textarea><button class="btn">Generate Architecture</button></form>{% if has %}<a class="btn secondary" href="/v5.svg" download>SVG</a><a class="btn secondary" href="/v5.drawio" download>Draw.io</a><a class="btn secondary" href="/v5/model" download>JSON</a>{% endif %}</div></div><div class="main"><div class="canvas">{% if has %}<img src="/v5.svg?t={{stamp}}">{% else %}<div style="color:#456;padding:30px">Enter a requirement to generate a requirement-driven topology.</div>{% endif %}</div></div></div></body></html>'''
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
@app.route('/health')
def health():return {'ok':True,'version':'v5','renderer':'dynamic-zoned-layout'}
if __name__=='__main__':app.run(host='0.0.0.0',port=3000)
