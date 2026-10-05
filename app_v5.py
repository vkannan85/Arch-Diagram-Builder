from flask import Flask,request,render_template_string,Response
import re,html,json,time,urllib.request,zipfile,io,base64
app=Flask(__name__); CURRENT=None
CIDR=r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'
ICON_ZIP='https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons_V24.zip'; ICONS={}
def esc(v): return html.escape(str(v or 'Not specified'))
def cidr_after(t,n):
 m=re.search(re.escape(n)+r'.{0,100}?('+CIDR+r')',t,re.I|re.S); return m.group(1) if m else None
def parse_requirement(t):
 low=t.lower(); hub=('hub-vnet' in low or ('hub' in low and 'spoke' in low))
 if hub:
  names=re.findall(r'\bSpoke\s*\d+[- ]?VNet\b|\bSpoke\d+-VNet\b',t,re.I) or ['Spoke1-VNet','Spoke2-VNet']; spokes=[]
  for raw in names:
   n=re.sub(r'\s+','',raw); n=n.replace('VNet','-VNet') if '-' not in n else n; n=n.replace('--','-')
   if any(x['name'].lower()==n.lower() for x in spokes):continue
   i=len(spokes)+1; mm=re.search(r'\bVM0?%d\b'%i,t,re.I); vm=mm.group(0).upper() if mm else 'VM%02d'%i
   spokes.append({'name':n,'cidr':cidr_after(t,n),'vm':vm})
  return {'type':'hubspoke','title':'Hub-and-Spoke Network Architecture','hub':{'name':'Hub-VNet','cidr':cidr_after(t,'Hub-VNet')},'spokes':spokes,'source':t}
 catalog=[('internet','Internet',['internet','public-facing']),('frontdoor','Azure Front Door',['front door']),('appgw','Application Gateway / WAF',['application gateway','web application firewall','waf']),('loadbalancer','Azure Load Balancer',['load balancer']),('vm','Virtual Machines',['virtual machine','windows server','web-vm',' vm']),('sql','Azure SQL Database',['sql database','azure sql']),('storage','Storage Account',['storage account']),('keyvault','Azure Key Vault',['key vault']),('monitor','Azure Monitor',['azure monitor']),('loganalytics','Log Analytics Workspace',['log analytics']),('privateendpoint','Private Endpoints',['private endpoint']),('nsg','Network Security Groups',['network security group','nsg'])]
 resources=[]
 for k,label,terms in catalog:
  if any(x in low for x in terms): resources.append({'id':k,'label':label})
 vn=re.search(r'([A-Za-z0-9-]+VNet)\s*[:\-]?\s*('+CIDR+r')',t,re.I)
 vnet={'name':vn.group(1) if vn else 'Virtual Network','cidr':vn.group(2) if vn else None} if ('vnet' in low or 'virtual network' in low) else None
 subnets=[]
 for name,cidr in re.findall(r'([A-Za-z][A-Za-z0-9 -]*subnet)\s*[:\-]?\s*('+CIDR+r')',t,re.I):
  item={'name':name.strip(),'cidr':cidr}
  if not any(s['cidr']==cidr for s in subnets):subnets.append(item)
 return {'type':'generic','title':'Azure Solution Architecture','vnet':vnet,'subnets':subnets,'resources':resources,'source':t}
def load_icons():
 global ICONS
 if ICONS:return
 try:
  data=urllib.request.urlopen(ICON_ZIP,timeout=20).read(); z=zipfile.ZipFile(io.BytesIO(data)); files=[n for n in z.namelist() if n.lower().endswith('.svg')]
  terms={'firewall':['firewalls'],'gateway':['virtual network gateways'],'expressroute':['expressroute circuits'],'vm':['virtual machines'],'frontdoor':['front doors'],'appgw':['application gateways'],'loadbalancer':['load balancers'],'sql':['sql database'],'storage':['storage accounts'],'keyvault':['key vaults'],'monitor':['monitor'],'loganalytics':['log analytics workspaces'],'privateendpoint':['private endpoints'],'nsg':['network security groups']}
  for k,words in terms.items():
   hits=[n for n in files if any(w in n.lower() for w in words) and 'classic' not in n.lower()]
   if hits:ICONS[k]=base64.b64encode(z.read(sorted(hits,key=len)[0])).decode()
 except Exception as e: print('icon pack:',e)
def icon(k,x,y,w=62,h=62):
 load_icons()
 if k in ICONS:return f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="data:image/svg+xml;base64,{ICONS[k]}"/>'
 return f'<g transform="translate({x},{y})"><rect width="{w}" height="{h}" rx="10" fill="#eef6fc" stroke="#0078d4"/><text x="{w/2}" y="{h/2+5}" text-anchor="middle" font-family="Arial" font-size="10" fill="#0067b8">{esc(k)}</text></g>'
def defs():return '<defs><marker id="end" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker><marker id="both" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M10 0L0 5L10 10z" fill="#0078d4"/></marker></defs>'
def text(x,y,s,z=16,w=400,a='start',c='#17324d'):return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial" font-size="{z}" font-weight="{w}" text-anchor="{a}" fill="{c}">{esc(s)}</text>'
def box(x,y,w,h,stroke='#75b9e7',fill='#fff',rx=16):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
def generic_svg(m):
 W,H=1840,980; A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs()}<rect width="100%" height="100%" fill="white"/>',text(45,58,m['title'],36,700),text(45,90,'Requirement-driven topology • only detected resources are shown',17,400,c='#5d7185')]
 res=m['resources']; by={r['id']:r for r in res}; public=[k for k in ['internet','frontdoor','appgw','loadbalancer'] if k in by]; private=[k for k in ['vm','sql','storage','keyvault','privateendpoint','nsg'] if k in by]; ops=[k for k in ['monitor','loganalytics'] if k in by]
 pos={}; x=70
 for k in public: pos[k]=(x,180); x+=250
 vx=880; vy=125; vw=880; vh=620
 if m['vnet'] or private:
  A += [box(vx,vy,vw,vh,'#0078d4','#f4faff',22),text(vx+28,vy+42,'Virtual Network',25,700),text(vx+28,vy+70,(m['vnet']['name']+' • '+(m['vnet']['cidr'] or 'CIDR not specified')) if m['vnet'] else 'Network boundary',16,400,c='#526a80')]
 cols=3
 for i,k in enumerate(private): pos[k]=(vx+70+(i%cols)*255,vy+125+(i//cols)*205)
 for k in ops: pos[k]=(1200+ops.index(k)*260,820)
 for k,(x,y) in pos.items():
  label=by[k]['label']; A += [box(x,y,190,130,'#8ab4d6','#fff',14),icon(k,x+64,y+16,62,62),text(x+95,y+105,label,14,700,'middle')]
 chain=[k for k in ['internet','frontdoor','appgw','loadbalancer','vm'] if k in pos]
 for a,b in zip(chain,chain[1:]):
  x1,y1=pos[a];x2,y2=pos[b]; A.append(f'<path d="M{x1+190} {y1+65} H{(x1+x2+190)//2} V{y2+65} H{x2}" fill="none" stroke="#0078d4" stroke-width="4" marker-end="url(#end)"/>')
 if 'vm' in pos:
  for k in ['sql','storage','keyvault']:
   if k in pos:
    x1,y1=pos['vm'];x2,y2=pos[k]; A.append(f'<path d="M{x1+95} {y1+130} V{y2-25} H{x2+95} V{y2}" fill="none" stroke="#0078d4" stroke-width="3" marker-end="url(#end)"/>')
 for k in ops:
  if 'vm' in pos:
   x1,y1=pos['vm'];x2,y2=pos[k];A.append(f'<path d="M{x1+95} {y1+130} V{y2-18} H{x2+95} V{y2}" fill="none" stroke="#6b7d90" stroke-width="2" stroke-dasharray="8 6" marker-end="url(#end)"/>')
 if m['subnets']:
  sy=vy+500
  for i,s in enumerate(m['subnets'][:3]):A += [text(vx+40+i*275,sy,s['name'],14,700),text(vx+40+i*275,sy+23,s['cidr'],13,400,c='#718295')]
 A += [text(45,H-35,'No unprovided IP addresses or resource names are invented.',14,400,c='#526a80'),'</svg>'];return ''.join(A)
def hub_svg(m):
 W,H=1840,980; A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs()}<rect width="100%" height="100%" fill="white"/>',text(45,58,m['title'],36,700),box(90,190,520,610,'#0078d4','#f4faff',22),text(120,235,'Hub Virtual Network',26,700),text(120,266,m['hub']['name']+' • '+(m['hub']['cidr'] or 'CIDR not specified'),16,400,c='#526a80'),box(150,330,400,160),icon('gateway',315,360),text(350,455,'ExpressRoute Gateway',16,700,'middle'),box(150,540,400,160),icon('firewall',315,570),text(350,665,'Azure Firewall',16,700,'middle')]
 for i,s in enumerate(m['spokes']):
  x,y=930,170+i*300;A += [box(x,y,650,240,'#39a869','#f5fff8',20),text(x+30,y+42,'Spoke Virtual Network',22,700),text(x+30,y+72,s['name']+' • '+(s['cidr'] or 'CIDR not specified'),16,400,c='#526a80'),icon('vm',x+470,y+105,70,70),text(x+505,y+200,s['vm']+' • Windows Server',14,700,'middle'),f'<path d="M610 {y+120} H930" stroke="#0078d4" stroke-width="4" marker-start="url(#both)" marker-end="url(#end)"/>']
 A.append('</svg>');return ''.join(A)
def svg(m):return hub_svg(m) if m.get('type')=='hubspoke' else generic_svg(m)
def drawio(m):
 # editable generic representation mirrors detected topology rather than a fixed template
 nodes=m.get('resources',[]); R=['<mxCell id="0"/><mxCell id="1" parent="0"/>']; x=80;y=120
 for i,n in enumerate(nodes):
  xx=x+(i%4)*330; yy=y+(i//4)*190; R.append(f'<mxCell id="n{i}" value="{esc(n["label"])}" style="rounded=1;whiteSpace=wrap;html=1;strokeColor=#0078d4;fillColor=#ffffff;" vertex="1" parent="1"><mxGeometry x="{xx}" y="{yy}" width="240" height="110" as="geometry"/></mxCell>')
 for i in range(max(0,len(nodes)-1)):R.append(f'<mxCell id="e{i}" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#0078d4;endArrow=block;" edge="1" parent="1" source="n{i}" target="n{i+1}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="V5 Dynamic Architecture"><mxGraphModel><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
PAGE='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Studio V5</title><style>body{margin:0;font-family:Arial;background:#07111f;color:#eef5ff}.top{padding:16px 22px;background:#0c1a2d;font-weight:800;font-size:20px}.top b{color:#39a8ff}.grid{display:grid;grid-template-columns:380px minmax(0,1fr);min-height:calc(100vh - 58px)}.side{padding:18px;background:#0c1a2d}.main{padding:18px;min-width:0}.card{background:#11243b;border:1px solid #29415e;border-radius:14px;padding:15px}textarea{width:100%;height:390px;box-sizing:border-box;background:#071522;color:white;border:1px solid #395675;border-radius:10px;padding:12px}.btn{display:inline-block;margin:10px 5px 0 0;background:#1688f8;color:white;border:0;border-radius:9px;padding:11px 15px;font-weight:700;text-decoration:none}.secondary{background:#29415e}.canvas{background:white;border-radius:14px;overflow:auto;max-height:82vh}.canvas img{display:block;width:100%;height:auto;max-width:1840px}@media(max-width:850px){.grid{display:block}.side,.main{padding:10px}.canvas{max-height:none}.canvas img{width:145%;max-width:none}textarea{height:300px}}</style></head><body><div class="top"><b>Azure</b> Architecture Studio <small>V5 Dynamic</small></div><div class="grid"><div class="side"><div class="card"><form method="post"><h3>Architecture requirement</h3><textarea name="req">{{req}}</textarea><button class="btn">Generate Architecture</button></form>{% if has %}<a class="btn secondary" href="/v5.svg" download>SVG</a><a class="btn secondary" href="/v5.drawio" download>Draw.io</a><a class="btn secondary" href="/v5/model" download>JSON</a>{% endif %}</div></div><div class="main"><div class="canvas">{% if has %}<img src="/v5.svg?t={{stamp}}">{% else %}<div style="color:#456;padding:30px">Enter a requirement to generate a requirement-driven topology.</div>{% endif %}</div></div></div></body></html>'''
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
def health():return {'ok':True,'version':'v5','renderer':'dynamic-requirement-topology-v1'}
if __name__=='__main__':app.run(host='0.0.0.0',port=3000)
