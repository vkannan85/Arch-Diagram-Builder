from flask import Flask,request,send_file,render_template_string,Response
import os,re,html,json,time
import cairosvg
app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,'diagrams'); os.makedirs(OUT,exist_ok=True)
SVG=os.path.join(OUT,'portal_v4.svg'); PNG=os.path.join(OUT,'portal_v4.png'); DRAWIO=os.path.join(OUT,'portal_v4.drawio'); MODEL=os.path.join(OUT,'portal_v4.json')
CIDR=r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}'
def cidr_after(t,label):
 m=re.search(re.escape(label)+r'.{0,100}?('+CIDR+r')',t,re.I|re.S); return m.group(1) if m else None
def subnet_near(t,vm):
 m=re.search(re.escape(vm)+r'.{0,120}?('+CIDR+r')',t,re.I|re.S) or re.search(r'('+CIDR+r').{0,120}?'+re.escape(vm),t,re.I|re.S); return m.group(1) if m else None
def interpret(t):
 return {'title':'Hub-and-Spoke Network Architecture','subtitle':'Secure connectivity between Azure workloads and On-Premises infrastructure','hub':{'name':'Hub-VNet','cidr':cidr_after(t,'Hub-VNet')},'spokes':[{'name':'Spoke1-VNet','cidr':cidr_after(t,'Spoke1-VNet'),'subnet':subnet_near(t,'VM01'),'vm':'VM01'},{'name':'Spoke2-VNet','cidr':cidr_after(t,'Spoke2-VNet'),'subnet':subnet_near(t,'VM02'),'vm':'VM02'}],'onprem':{'name':'On-Premises Datacentre','cidr':None},'peering':{'allow_forwarded_traffic':bool(re.search('forwarded traffic',t,re.I)),'allow_gateway_transit':bool(re.search('gateway transit',t,re.I)),'use_remote_gateway':bool(re.search('remote gateway',t,re.I))},'source':t}
def E(v): return html.escape(str(v if v else 'Not specified'))
def svg(m):
 h=m['hub']; spokes=m['spokes']; p=m['peering']
 def txt(x,y,v,size=18,weight=400,anchor='start',fill='#172b4d'): return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{E(v)}</text>'
 def box(x,y,w,hh,stroke,fill,rx=16,sw=3): return f'<rect x="{x}" y="{y}" width="{w}" height="{hh}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
 def vm(x,y): return f'<g transform="translate({x},{y})"><rect x="0" y="0" width="70" height="48" rx="5" fill="#0078d4"/><rect x="8" y="8" width="54" height="32" fill="white"/><path d="M28 51h15v9H28zM18 60h35v5H18z" fill="#0078d4"/></g>'
 def gw(x,y): return f'<g transform="translate({x},{y})"><circle cx="38" cy="38" r="36" fill="#0078d4"/><path d="M17 38h42M38 17v42M24 25l-8 13 8 13M52 25l8 13-8 13" fill="none" stroke="white" stroke-width="5"/></g>'
 def er(x,y): return f'<g transform="translate({x},{y})"><circle cx="38" cy="38" r="36" fill="#0078d4"/><path d="M15 38h46M24 25L14 38l10 13M52 25l10 13-10 13" fill="none" stroke="white" stroke-width="5"/></g>'
 def fw(x,y): return f'<g transform="translate({x},{y})"><rect width="78" height="62" rx="4" fill="#e85d04"/><path d="M7 8h18v12H7zm23 0h18v12H30zm23 0h18v12H53zM7 25h28v12H7zm33 0h31v12H40zM7 42h18v12H7zm23 0h18v12H30zm23 0h18v12H53z" fill="white"/></g>'
 a=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">','<defs><marker id="end" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0078d4"/></marker><marker id="start" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10 0L0 5L10 10z" fill="#0078d4"/></marker></defs>','<rect width="1600" height="900" fill="white"/>']
 a += [txt(50,55,m['title'],35,700),txt(50,84,m['subtitle'],17,400,fill='#52677d')]
 a += [box(45,185,235,345,'#8796a5','#f5f7f9'),txt(162,225,'On-Premises',22,700,'middle'),txt(162,252,m['onprem']['name'],15,400,'middle','#52677d'),'<g stroke="#657786" stroke-width="3" fill="#dfe5ea"><rect x="82" y="310" width="34" height="115" rx="4"/><rect x="126" y="310" width="34" height="115" rx="4"/><rect x="170" y="310" width="34" height="115" rx="4"/></g>',txt(162,462,'Network',17,700,'middle'),txt(162,488,'CIDR not specified',14,400,'middle','#687b8d')]
 a += [er(322,320),txt(360,416,'ExpressRoute',18,700,'middle'),txt(360,440,'Circuit',18,700,'middle'),'<path d="M280 358H322" stroke="#0078d4" stroke-width="4" marker-end="url(#end)"/>']
 a += [box(455,125,515,580,'#1688f8','#f5fbff'),txt(485,166,'Hub Virtual Network',25,700),txt(485,197,f"{h['name']}  •  {h['cidr'] or 'CIDR not specified'}",17,400,fill='#52677d')]
 a += [box(505,245,415,170,'#79bdf2','#fff',14),txt(530,276,'GatewaySubnet',17,700),txt(530,301,'CIDR not specified',14,400,fill='#687b8d'),gw(674,305),txt(712,398,'ExpressRoute Gateway',18,700,'middle')]
 a += [box(505,475,415,170,'#79bdf2','#fff',14),txt(530,506,'AzureFirewallSubnet',17,700),txt(530,531,'CIDR not specified',14,400,fill='#687b8d'),fw(673,545),txt(712,630,'Azure Firewall',18,700,'middle')]
 a += ['<path d="M398 358H505" stroke="#0078d4" stroke-width="4" marker-end="url(#end)"/>','<path d="M920 350H1015V275H1070" fill="none" stroke="#0078d4" stroke-width="4" marker-start="url(#start)" marker-end="url(#end)"/>','<path d="M920 560H1015V570H1070" fill="none" stroke="#0078d4" stroke-width="4" marker-start="url(#start)" marker-end="url(#end)"/>']
 for i,sp in enumerate(spokes):
  y=145+i*300
  a += [box(1070,y,475,260,'#38a169','#f6fff8'),txt(1100,y+38,f'Spoke Virtual Network 0{i+1}',22,700),txt(1100,y+68,f"{sp['name']}  •  {sp['cidr'] or 'CIDR not specified'}",16,400,fill='#52677d'),box(1110,y+95,395,125,'#8bc8ee','#fff',12),txt(1135,y+125,'Workload Subnet',16,700),txt(1135,y+150,sp['subnet'] or 'CIDR not specified',14,400,fill='#687b8d'),vm(1325,y+120),txt(1360,y+207,f"{sp['vm']} • Windows Server",15,700,'middle')]
 a += [txt(995,228,'VNet Peering',15,700,'middle'),txt(995,250,'Hub → Spoke: gateway transit + forwarded traffic',12,400,'middle','#52677d'),txt(995,675,'Spoke → Hub: remote gateway + forwarded traffic',12,400,'middle','#52677d')]
 a += [box(45,735,390,125,'#d5dde5','#fafbfc',12,2),txt(70,765,'Legend',17,700),'<line x1="70" y1="795" x2="120" y2="795" stroke="#0078d4" stroke-width="4" marker-end="url(#end)"/>',txt(135,801,'Private connectivity / routing',14),'<rect x="70" y="820" width="28" height="20" rx="4" fill="#f6fff8" stroke="#38a169" stroke-width="2"/>',txt(112,836,'Spoke virtual network',14)]
 a += [box(455,735,1090,125,'#d5dde5','#fafbfc',12,2),txt(480,765,'Key Points',17,700),txt(480,795,'• GatewaySubnet and AzureFirewallSubnet CIDRs were not supplied; no CIDRs are invented.',14),txt(480,822,'• Hub and spokes use VNet peering with gateway transit / remote gateway as requested.',14),txt(480,849,'• Use UDRs on spoke subnets when traffic must be forced through Azure Firewall.',14)]
 a.append('</svg>'); return ''.join(a)
def drawio(m):
 def c(i,v,x,y,w,h,sty,parent='1'): return f'<mxCell id="{i}" value="{html.escape(v)}" style="{sty}" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
 R=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; h=m['hub']; s=m['spokes']
 R += [c('op','On-Premises Datacentre&#xa;CIDR not specified',45,185,235,345,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f7f9;strokeColor=#8796a5;fontSize=18;'),c('er','ExpressRoute Circuit',322,320,76,76,'ellipse;html=1;fillColor=#0078d4;fontColor=#ffffff;'),c('hub','Hub Virtual Network&#xa;Hub-VNet • '+(h['cidr'] or 'CIDR not specified'),455,125,515,580,'swimlane;rounded=1;html=1;startSize=75;container=1;collapsible=0;strokeColor=#1688f8;fillColor=#f5fbff;fontSize=18;')]
 R += [c('gw','GatewaySubnet&#xa;CIDR not specified&#xa;ExpressRoute Gateway',50,120,415,170,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#79bdf2;fillColor=#ffffff;fontSize=16;','hub'),c('fw','AzureFirewallSubnet&#xa;CIDR not specified&#xa;Azure Firewall',50,350,415,170,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#79bdf2;fillColor=#ffffff;fontSize=16;','hub')]
 for i,sp in enumerate(s,1):
  y=145+(i-1)*300; sid=f's{i}'; R += [c(sid,f"Spoke Virtual Network 0{i}&#xa;{sp['name']} • {sp['cidr'] or 'CIDR not specified'}",1070,y,475,260,'swimlane;rounded=1;html=1;startSize=75;container=1;collapsible=0;strokeColor=#38a169;fillColor=#f6fff8;fontSize=17;'),c(f'vm{i}',f"Workload Subnet • {sp['subnet'] or 'CIDR not specified'}&#xa;{sp['vm']} • Windows Server",40,95,395,125,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#8bc8ee;fillColor=#ffffff;fontSize=15;',sid)]
 for eid,a,b,l in [('e1','op','er','ExpressRoute'),('e2','er','gw','Private connectivity'),('e3','hub','s1','VNet Peering'),('e4','hub','s2','VNet Peering')]: R.append(f'<mxCell id="{eid}" value="{l}" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#0078d4;strokeWidth=3;startArrow=block;endArrow=block;" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="Azure Architecture"><mxGraphModel page="1" pageWidth="1600" pageHeight="900"><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
def review(m): return '\n'.join(['✓ Structured Hub-and-Spoke layout generated.','✓ ExpressRoute, Gateway, Firewall and workload hierarchy shown.','ℹ Unspecified network CIDRs are not invented.','⚠ Validate UDRs if traffic must traverse Azure Firewall.'])
def render(m):
 open(MODEL,'w').write(json.dumps(m,indent=2)); data=svg(m); open(SVG,'w').write(data); open(DRAWIO,'w').write(drawio(m)); cairosvg.svg2png(bytestring=data.encode(),write_to=PNG,output_width=1600,output_height=900)
HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Azure Architecture Studio</title><style>*{box-sizing:border-box}body{margin:0;font-family:Arial;background:#07111f;color:#e8f0ff}.top{padding:18px 22px;background:#0b1728;border-bottom:1px solid #20314a}.brand{font-size:20px;font-weight:800}.brand span{color:#39a8ff}.layout{display:grid;grid-template-columns:390px 1fr;min-height:calc(100vh - 64px)}.side,.main{padding:18px}.side{background:#0b1728;border-right:1px solid #20314a}.card{background:#101f33;border:1px solid #263a55;border-radius:14px;padding:16px;margin-bottom:14px}textarea{width:100%;min-height:280px;background:#081522;color:white;border:1px solid #36506f;border-radius:10px;padding:13px}.refine{min-height:75px}.btn{border:0;border-radius:9px;padding:10px 13px;font-weight:700;background:#1688f8;color:white;margin:7px 5px 0 0;cursor:pointer;text-decoration:none;display:inline-block}.btn2{background:#243c59}.canvas{height:72vh;min-height:560px;background:white;border-radius:14px;overflow:auto;padding:10px}.stage{transform-origin:top left;width:1600px}.stage img{width:1600px;height:900px;display:block}.muted{color:#94a9c3;font-size:13px}.review{white-space:pre-wrap;color:#cfe1f7}.toolbar{margin:0 0 10px}@media(max-width:850px){.layout{display:block}.side{border:0}.canvas{height:68vh;min-height:430px}.main{padding:10px}.side{padding:10px}.top{padding:12px 14px}}</style></head><body><div class=top><div class=brand><span>Azure</span> Architecture Studio</div><div class=muted>Professional architecture canvas • Editable Draw.io • 1600 × 900 export</div></div><div class=layout><aside class=side><div class=card><form method=post action=/generate><b>Architecture requirement</b><textarea name=requirements placeholder="Describe the Azure architecture...">{{requirement_text}}</textarea><button class=btn>Generate Architecture</button></form></div>{% if has %}<div class=card><form method=post action=/refine><b>Refine</b><textarea class=refine name=refinement placeholder="e.g. add another spoke"></textarea><button class=btn>Apply Refinement</button></form></div><div class=card><b>Architecture Review</b><div class=review>{{review_text}}</div></div>{% endif %}</aside><main class=main>{% if has %}<div class=toolbar><a class=btn href=/png>Download PNG</a><a class="btn btn2" href=/drawio>Download Draw.io</a><a class="btn btn2" href=/model>Architecture JSON</a><button class="btn btn2" onclick="zoom(-.1)">−</button><button class="btn btn2" onclick="fit()">Fit</button><button class="btn btn2" onclick="one()">100%</button><button class="btn btn2" onclick="zoom(.1)">+</button><button class="btn btn2" onclick="full()">Full Screen</button></div><div class=canvas id=canvas><div class=stage id=stage><img src="/svg?v={{stamp}}"></div></div>{% else %}<div class=card><h2>Enter an architecture requirement to generate the diagram.</h2></div>{% endif %}</main></div><script>let scale=1;function apply(){document.getElementById('stage').style.transform='scale('+scale+')';document.getElementById('stage').style.width=(1600*scale)+'px';document.getElementById('stage').style.height=(900*scale)+'px'}function zoom(d){scale=Math.max(.25,Math.min(2,scale+d));apply()}function fit(){let c=document.getElementById('canvas');scale=Math.max(.25,(c.clientWidth-24)/1600);apply()}function one(){scale=1;apply()}function full(){let c=document.getElementById('canvas');if(c.requestFullscreen)c.requestFullscreen()}window.addEventListener('load',()=>{if(window.innerWidth<850){scale=.65;apply()}else fit()})</script></body></html>'''
CURRENT=None
def page():
 global CURRENT
 return render_template_string(HTML,has=CURRENT is not None,requirement_text=CURRENT['source'] if CURRENT else '',review_text=review(CURRENT) if CURRENT else '',stamp=int(time.time()))
@app.get('/')
def home(): return page()
@app.get('/health')
def health(): return {'ok':True,'renderer':'svg-v2','canvas':'1600x900'}
@app.post('/generate')
def generate():
 global CURRENT; CURRENT=interpret(request.form.get('requirements','')); render(CURRENT); return page()
@app.post('/refine')
def refine():
 global CURRENT
 if CURRENT:
  r=request.form.get('refinement',''); CURRENT['source']+='\nRefinement: '+r
  if re.search(r'third spoke|spoke ?3',r,re.I) and len(CURRENT['spokes'])<3: CURRENT['spokes'].append({'name':'Spoke3-VNet','cidr':None,'subnet':None,'vm':'VM03'})
  render(CURRENT)
 return page()
@app.get('/svg')
def gets(): return Response(open(SVG).read(),mimetype='image/svg+xml') if os.path.exists(SVG) else ('No diagram',404)
@app.get('/png')
def getp(): return send_file(PNG,as_attachment=True,download_name='azure-architecture.png')
@app.get('/drawio')
def getd(): return send_file(DRAWIO,as_attachment=True,download_name='azure-architecture.drawio')
@app.get('/model')
def getm(): return send_file(MODEL,as_attachment=True,download_name='architecture.json')
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',3000)))