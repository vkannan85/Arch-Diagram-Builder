from flask import Flask,request,send_file,render_template_string,Response
import os,re,html,json,time
import cairosvg
app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,'diagrams'); os.makedirs(OUT,exist_ok=True)
SVG=os.path.join(OUT,'portal_v4.svg'); PNG=os.path.join(OUT,'portal_v4.png'); DRAWIO=os.path.join(OUT,'portal_v4.drawio'); MODEL=os.path.join(OUT,'portal_v4.json')

def cidr_after(t,label):
 m=re.search(re.escape(label)+r'.{0,100}?(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})',t,re.I|re.S); return m.group(1) if m else None
def subnet_near(t,vm):
 m=re.search(re.escape(vm)+r'.{0,100}?(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})',t,re.I|re.S)
 if not m:m=re.search(r'(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}).{0,100}?'+re.escape(vm),t,re.I|re.S)
 return m.group(1) if m else None
def interpret(t):
 hub=cidr_after(t,'Hub-VNet'); s1=cidr_after(t,'Spoke1-VNet'); s2=cidr_after(t,'Spoke2-VNet')
 return {'title':'Hub-and-Spoke Network Architecture','subtitle':'Secure connectivity between Azure workloads and On-Premises infrastructure','hub':{'name':'Hub-VNet','cidr':hub,'firewall':'firewall' in t.lower(),'expressroute_gateway':bool(re.search(r'express\s*route gateway',t,re.I))},'spokes':[{'name':'Spoke1-VNet','cidr':s1,'subnet':subnet_near(t,'VM01') or cidr_after(t,'subnet'),'vm':'VM01'},{'name':'Spoke2-VNet','cidr':s2,'subnet':subnet_near(t,'VM02'),'vm':'VM02'}],'onprem':{'name':'On-Premises Datacentre','cidr':None},'expressroute':bool(re.search(r'express\s*route',t,re.I)),'peering':{'allow_forwarded_traffic':bool(re.search('forwarded traffic',t,re.I)),'allow_gateway_transit':bool(re.search('gateway transit',t,re.I)),'use_remote_gateway':bool(re.search('remote gateway',t,re.I))},'source':t}
def E(x):return html.escape(str(x or 'Not specified'))
def svg(m):
 h=m['hub']; s=m['spokes']; p=m['peering'];
 def txt(x,y,v,size=18,weight=400,anchor='start',fill='#172b4d'):return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{E(v)}</text>'
 def box(x,y,w,hh,stroke,fill,rx=18):return f'<rect x="{x}" y="{y}" width="{w}" height="{hh}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
 def icon(x,y,kind):
  if kind=='fw': return f'<g transform="translate({x},{y})"><path d="M8 12h58v44H8z" fill="#e85d04"/><path d="M12 17h13v10H12zm17 0h13v10H29zm17 0h16v10H46zM12 31h20v10H12zm24 0h26v10H36zM12 45h13v7H12zm17 0h13v7H29zm17 0h16v7H46z" fill="white"/></g>'
  if kind=='gw': return f'<g transform="translate({x},{y})"><circle cx="36" cy="34" r="31" fill="#0078d4"/><path d="M18 34h36M36 16v36M24 22l-7 12 7 12M48 22l7 12-7 12" fill="none" stroke="white" stroke-width="5"/></g>'
  if kind=='er': return f'<g transform="translate({x},{y})"><circle cx="34" cy="34" r="31" fill="#0078d4"/><path d="M13 34h42M21 23l-9 11 9 11M47 23l9 11-9 11" fill="none" stroke="white" stroke-width="5"/></g>'
  if kind=='vm': return f'<g transform="translate({x},{y})"><rect x="5" y="7" width="62" height="43" rx="4" fill="#0078d4"/><rect x="12" y="14" width="48" height="29" fill="white"/><path d="M28 54h17v8H28zM20 62h34v5H20z" fill="#0078d4"/></g>'
  return ''
 flags=[]
 if p['allow_forwarded_traffic']:flags.append('Forwarded traffic')
 if p['allow_gateway_transit']:flags.append('Gateway transit')
 if p['use_remote_gateway']:flags.append('Remote gateway')
 peer=' • '.join(flags) or 'VNet peering'
 a=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">','<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker></defs>','<rect width="1600" height="900" fill="white"/>']
 a += [txt(55,58,m['title'],34,700),txt(55,88,m['subtitle'],17,400,fill='#52677d')]
 # on-prem
 a += [box(45,185,245,355,'#8796a5','#f5f7f9'),txt(168,225,'On-Premises',22,700,'middle'),txt(168,255,m['onprem']['name'],16,400,'middle','#52677d'),'<g stroke="#657786" stroke-width="3" fill="#dfe5ea">'+''.join(f'<rect x="{90+i*48}" y="310" width="34" height="120" rx="4"/>' for i in range(3))+'</g>',txt(168,470,'Network',17,700,'middle'),txt(168,496,'CIDR not specified',14,400,'middle','#687b8d')]
 # ER
 a += [icon(340,315,'er'),txt(374,410,'ExpressRoute',18,700,'middle'),txt(374,434,'Circuit',18,700,'middle'),f'<path d="M290 350H340" stroke="#0078d4" stroke-width="4" marker-end="url(#arr)"/>']
 # hub
 a += [box(470,125,520,610,'#1688f8','#f5fbff'),txt(500,165,'Hub Virtual Network',24,700),txt(500,195,f"{h['name']}  •  {h['cidr'] or 'CIDR not specified'}",17,400,fill='#52677d')]
 a += [box(525,250,410,175,'#79bdf2','#ffffff',14),txt(550,280,'GatewaySubnet',16,700),txt(550,305,'CIDR not specified',14,400,fill='#687b8d'),icon(690,315,'gw'),txt(726,400,'ExpressRoute Gateway',18,700,'middle')]
 a += [box(525,480,410,175,'#79bdf2','#ffffff',14),txt(550,510,'AzureFirewallSubnet',16,700),txt(550,535,'CIDR not specified',14,400,fill='#687b8d'),icon(690,550,'fw'),txt(726,635,'Azure Firewall',18,700,'middle')]
 a += [f'<path d="M408 350H525" stroke="#0078d4" stroke-width="4" marker-end="url(#arr)"/>',f'<path d="M730 425V480" stroke="#0078d4" stroke-width="4" marker-end="url(#arr)"/>']
 # spokes
 for i,sp in enumerate(s):
  y=145+i*315
  a += [box(1080,y,455,270,'#38a169','#f6fff8'),txt(1110,y+38,f'Spoke Virtual Network 0{i+1}',22,700),txt(1110,y+68,f"{sp['name']}  •  {sp['cidr'] or 'CIDR not specified'}",16,400,fill='#52677d'),box(1120,y+95,375,135,'#8bc8ee','#ffffff',12),txt(1145,y+125,'Workload Subnet',15,700),txt(1145,y+151,sp['subnet'] or 'CIDR not specified',14,400,fill='#687b8d'),icon(1310,y+145,'vm'),txt(1347,y+225,f"{sp['vm']} • Windows Server",15,700,'middle')]
  sy=335 if i==0 else 570
  a += [f'<path d="M935 {sy}H1035V{y+155}H1080" fill="none" stroke="#0078d4" stroke-width="4" marker-start="url(#arr)" marker-end="url(#arr)"/>',txt(1030,y+125,'VNet Peering',14,700,'end'),txt(1030,y+147,peer,11,400,'end','#52677d')]
 # footer
 a += [box(45,770,1490,95,'#d5dde5','#fafbfc',12),txt(70,802,'Architecture notes',17,700),txt(70,829,'GatewaySubnet and AzureFirewallSubnet CIDRs were not supplied, so the diagram does not invent them.',14),txt(70,851,'Use UDRs on spoke subnets when traffic must be forced through Azure Firewall.',14)]
 a.append('</svg>');return ''.join(a)
def drawio(m):
 def c(i,v,x,y,w,h,sty,parent='1'):return f'<mxCell id="{i}" value="{html.escape(v)}" style="{sty}" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
 R=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; h=m['hub']; s=m['spokes']
 R += [c('op','On-Premises Datacentre&#xa;CIDR not specified',45,185,245,355,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f7f9;strokeColor=#8796a5;fontSize=18;'),c('er','ExpressRoute Circuit',340,315,90,90,'shape=mxgraph.azure.express_route_circuits;html=1;verticalLabelPosition=bottom;verticalAlign=top;'),c('hub','Hub Virtual Network&#xa;Hub-VNet • '+(h['cidr'] or 'CIDR not specified'),470,125,520,610,'swimlane;rounded=1;html=1;startSize=70;container=1;collapsible=0;strokeColor=#1688f8;fillColor=#f5fbff;fontSize=18;')]
 R += [c('gw','GatewaySubnet&#xa;CIDR not specified&#xa;ExpressRoute Gateway',55,125,410,175,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#79bdf2;fillColor=#ffffff;fontSize=16;','hub'),c('fw','AzureFirewallSubnet&#xa;CIDR not specified&#xa;Azure Firewall',55,355,410,175,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#79bdf2;fillColor=#ffffff;fontSize=16;','hub')]
 for i,sp in enumerate(s,1):
  y=145+(i-1)*315; sid=f's{i}'; R += [c(sid,f"Spoke Virtual Network 0{i}&#xa;{sp['name']} • {sp['cidr'] or 'CIDR not specified'}",1080,y,455,270,'swimlane;rounded=1;html=1;startSize=75;container=1;collapsible=0;strokeColor=#38a169;fillColor=#f6fff8;fontSize=17;'),c(f'vm{i}',f"Workload Subnet • {sp['subnet'] or 'CIDR not specified'}&#xa;{sp['vm']} • Windows Server",40,100,375,125,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#8bc8ee;fillColor=#ffffff;fontSize=15;',sid)]
 for eid,a,b,l in [('e1','op','er','ExpressRoute'),('e2','er','gw','Private connectivity'),('e3','gw','fw','Hub routing'),('e4','fw','vm1','VNet Peering'),('e5','fw','vm2','VNet Peering')]:R.append(f'<mxCell id="{eid}" value="{l}" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#0078d4;strokeWidth=3;endArrow=block;" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="Azure Architecture"><mxGraphModel page="1" pageWidth="1600" pageHeight="900"><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
def review(m):
 a=['✓ Structured Hub-and-Spoke layout generated.','✓ ExpressRoute, Gateway, Firewall and workload hierarchy shown.']
 if not m['onprem']['cidr']:a.append('ℹ On-premises CIDR not supplied; none invented.')
 a += ['ℹ GatewaySubnet/AzureFirewallSubnet CIDRs not supplied; none invented.','⚠ Validate UDRs if traffic must traverse Azure Firewall.'];return '\n'.join(a)
def render(m):
 open(MODEL,'w').write(json.dumps(m,indent=2)); data=svg(m);open(SVG,'w').write(data);open(DRAWIO,'w').write(drawio(m));cairosvg.svg2png(bytestring=data.encode(),write_to=PNG,output_width=1600,output_height=900)
HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Azure Architecture Studio</title><style>*{box-sizing:border-box}body{margin:0;font-family:Arial;background:#07111f;color:#e8f0ff}.top{padding:18px 22px;background:#0b1728;border-bottom:1px solid #20314a}.brand{font-size:20px;font-weight:800}.brand span{color:#39a8ff}.layout{display:grid;grid-template-columns:390px 1fr;min-height:calc(100vh - 64px)}.side,.main{padding:18px}.side{background:#0b1728;border-right:1px solid #20314a}.card{background:#101f33;border:1px solid #263a55;border-radius:14px;padding:16px;margin-bottom:14px}textarea{width:100%;min-height:300px;background:#081522;color:white;border:1px solid #36506f;border-radius:10px;padding:13px}.refine{min-height:80px}.btn{border:0;border-radius:9px;padding:10px 13px;font-weight:700;background:#1688f8;color:white;margin:7px 5px 0 0;cursor:pointer;text-decoration:none;display:inline-block}.btn2{background:#243c59}.toolbar{margin-top:10px}.canvas{height:70vh;min-height:560px;background:white;border-radius:14px;overflow:auto;padding:12px}.stage{transform-origin:top left;width:1600px}.stage img{width:1600px;height:900px;display:block}.muted{color:#94a9c3;font-size:13px}.review{white-space:pre-wrap;color:#cfe1f7}@media(max-width:850px){.layout{grid-template-columns:1fr}.side{border-right:0}.canvas{height:62vh}.top .muted{display:none}}</style></head><body><div class=top><div class=brand><span>Azure</span> Architecture Studio</div><div class=muted>Controlled architecture canvas • Editable Draw.io • 1600 × 900 export</div></div><div class=layout><aside class=side><div class=card><h3>Architecture requirement</h3><form method=post action=/generate><textarea name=requirements>{{req}}</textarea><button class=btn>Generate Diagram</button></form></div>{% if ready %}<div class=card><h3>Refine current diagram</h3><form method=post action=/refine><textarea class=refine name=refinement placeholder="Describe a change"></textarea><button class=btn>Apply Changes</button></form></div><div class=card><h3>Architecture review</h3><div class=review>{{review}}</div></div>{% endif %}</aside><main class=main><div class=card><h3>Diagram preview</h3>{% if ready %}<a class="btn btn2" href=/png>Download PNG</a><a class="btn btn2" href=/svg>Download SVG</a><a class="btn btn2" href=/drawio>Download Draw.io</a><a class="btn btn2" href=/model>Architecture JSON</a><div class=toolbar><button class="btn btn2" type=button onclick="fit()">Fit</button><button class="btn btn2" type=button onclick="zoom(-.1)">−</button><button class="btn btn2" type=button onclick="one()">100%</button><button class="btn btn2" type=button onclick="zoom(.1)">+</button></div>{% endif %}</div><div class=canvas id=canvas>{% if ready %}<div class=stage id=stage><img src="/svg?t={{stamp}}"></div>{% else %}<div style="color:#53677e;padding:40px">Enter a requirement to generate the architecture.</div>{% endif %}</div></main></div><script>let z=1;function setz(){let s=document.getElementById('stage');if(!s)return;s.style.transform='scale('+z+')';s.style.width=(1600*z)+'px';s.style.height=(900*z)+'px'}function zoom(d){z=Math.max(.25,Math.min(2,z+d));setz()}function one(){z=1;setz()}function fit(){let c=document.getElementById('canvas');if(!c)return;z=Math.min(1,(c.clientWidth-24)/1600);setz()}window.addEventListener('load',fit);window.addEventListener('resize',fit)</script></body></html>'''
def page(req='',ready=False,error=None):return render_template_string(HTML,req=req,ready=ready,error=error,review=review(json.load(open(MODEL))) if ready and os.path.exists(MODEL) else '',stamp=time.time())
@app.get('/')
def home():return page()
@app.get('/health')
def health():return {'status':'ok','renderer':'controlled-svg','canvas':'1600x900'}
@app.post('/generate')
def generate():
 req=request.form.get('requirements','').strip()
 if not req:return page(error='Please enter an architecture requirement.')
 try:m=interpret(req);render(m);return page(req,True)
 except Exception as e:return page(req,False,error=str(e))
@app.post('/refine')
def refine():
 if not os.path.exists(MODEL):return page(error='Generate a diagram first.')
 m=json.load(open(MODEL));r=request.form.get('refinement','').strip();m['source']+='\nRefinement: '+r;render(m);return page(m['source'],True)
@app.get('/svg')
def getsvg():return send_file(SVG,mimetype='image/svg+xml',as_attachment=request.args.get('download')=='1',download_name='azure-architecture.svg')
@app.get('/png')
def getpng():return send_file(PNG,as_attachment=True,download_name='azure-architecture.png')
@app.get('/drawio')
def getdrawio():return send_file(DRAWIO,as_attachment=True,download_name='azure-architecture.drawio')
@app.get('/model')
def getmodel():return send_file(MODEL,as_attachment=True,download_name='architecture.json')
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',3000)))
