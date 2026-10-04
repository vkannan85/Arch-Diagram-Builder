from flask import Flask,request,send_file,render_template_string
import os,re,html,json,subprocess,shutil,time,glob,sys
app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,'diagrams'); os.makedirs(OUT,exist_ok=True)
PNG=os.path.join(OUT,'portal_v4.png'); DRAWIO=os.path.join(OUT,'portal_v4.drawio'); MODEL=os.path.join(OUT,'portal_v4.json')

def icon_index():
 roots=[]
 for p in sys.path:
  r=os.path.join(p,'resources','azure')
  if os.path.isdir(r): roots.append(r)
 files=[]
 for r in roots: files += glob.glob(os.path.join(r,'**','*.png'),recursive=True)
 return files
ICONS=icon_index()
def icon(*words):
 for f in ICONS:
  n=os.path.basename(f).lower().replace('-','').replace('_','')
  if all(w.lower().replace(' ','') in n for w in words): return f
 return ''
ICONMAP={
 'vnet':icon('virtual','network'),
 'firewall':icon('firewall'),
 'gateway':icon('virtual','network','gateway') or icon('gateway'),
 'expressroute':icon('express','route'),
 'vm':icon('virtual','machine') or icon('vm'),
}

def cidr_after(t,label):
 m=re.search(re.escape(label)+r'.{0,100}?(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})',t,re.I|re.S); return m.group(1) if m else None
def interpret(t):
 hub=cidr_after(t,'Hub-VNet'); s1=cidr_after(t,'Spoke1-VNet'); s2=cidr_after(t,'Spoke2-VNet')
 cidrs=re.findall(r'\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b',t)
 subs=[x for x in cidrs if x not in [hub,s1,s2]]
 onprem=None
 m=re.search(r'(?:on-premises|on premises|on-prem).{0,120}?(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})',t,re.I|re.S)
 if m:onprem=m.group(1)
 return {'title':'Hub-and-Spoke Network Architecture','subtitle':'Secure connectivity between Azure workloads and On-Premises infrastructure','hub':{'name':'Hub-VNet','cidr':hub,'firewall':bool(re.search('firewall',t,re.I)),'expressroute_gateway':bool(re.search('expressroute gateway|express route gateway',t,re.I))},'spokes':[{'name':'Spoke1-VNet','cidr':s1,'subnet':subs[0] if len(subs)>0 else None,'vm':'VM01'},{'name':'Spoke2-VNet','cidr':s2,'subnet':subs[1] if len(subs)>1 else None,'vm':'VM02'}],'onprem':{'name':'On-Premises Datacentre','cidr':onprem},'expressroute':bool(re.search('expressroute|express route',t,re.I)),'peering':{'allow_forwarded_traffic':bool(re.search('forwarded traffic',t,re.I)),'allow_gateway_transit':bool(re.search('gateway transit',t,re.I)),'use_remote_gateway':bool(re.search('remote gateway',t,re.I))},'source':t}
def esc(x):return html.escape(x or 'Not specified')
def img_html(path,w=58,h=58):
 return f'<IMG SRC="{path}" SCALE="TRUE" FIXEDSIZE="TRUE" WIDTH="{w}" HEIGHT="{h}"/>' if path else '<FONT POINT-SIZE="28" COLOR="#1688f8">◆</FONT>'
def node_html(title,subtitle,kind):
 return '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="3" CELLPADDING="2"><TR><TD>'+img_html(ICONMAP.get(kind,''))+'</TD></TR><TR><TD><B>'+esc(title)+'</B></TD></TR><TR><TD><FONT POINT-SIZE="10">'+esc(subtitle)+'</FONT></TD></TR></TABLE>>'
def dot(m):
 h=m['hub']; sp=m['spokes']; op=m['onprem']; p=m['peering']
 L=['digraph G {','graph [rankdir=LR,bgcolor="white",pad="0.45",nodesep="0.6",ranksep="1.0",splines=ortho,fontname="Arial"];','node [shape=plain,fontname="Arial",fontsize=12];','edge [fontname="Arial",fontsize=9,color="#1565c0",penwidth=2,arrowsize=.7];']
 L+=['labelloc="t"; label=<<FONT POINT-SIZE="22"><B>'+esc(m['title'])+'</B></FONT><BR/><FONT POINT-SIZE="12">'+esc(m['subtitle'])+'</FONT>>;']
 L+=['subgraph cluster_op {label="On-Premises";style="rounded,filled";fillcolor="#f4f6f8";color="#7a8794";penwidth=1.5; op [label='+node_html(op['name'],op['cidr'],'vnet')+'];}']
 L+=['erc [label='+node_html('ExpressRoute Circuit','Private connectivity','expressroute')+'];']
 L+=['subgraph cluster_h {label="Hub Virtual Network\\n'+esc(h['name'])+'  '+esc(h['cidr'])+'";style="rounded,filled";fillcolor="#f4faff";color="#1688f8";penwidth=2;fontsize=16;']
 if h['firewall']:L+=['fw [label='+node_html('Azure Firewall','Centralised traffic inspection • routing • security policy','firewall')+'];']
 if h['expressroute_gateway']:L+=['gw [label='+node_html('ExpressRoute Gateway','GatewaySubnet • private connectivity','gateway')+'];']
 L+=['}']
 for i,s in enumerate(sp,1):
  L+=['subgraph cluster_s'+str(i)+' {label="Spoke Virtual Network 0'+str(i)+'\\n'+esc(s['name'])+'  '+esc(s['cidr'])+'";style="rounded,filled";fillcolor="#f5fff7";color="#2e8b57";penwidth=2;fontsize=15;','sub'+str(i)+' [label=<<TABLE BORDER="1" COLOR="#82b6e8" STYLE="ROUNDED" CELLBORDER="0" CELLPADDING="9"><TR><TD><B>Subnet</B></TD></TR><TR><TD>'+esc(s['subnet'])+'</TD></TR></TABLE>>];','vm'+str(i)+' [label='+node_html(s['vm'],'Windows Server VM','vm')+'];','sub'+str(i)+' -> vm'+str(i)+' [label=" hosts ",color="#7a8794"];','}']
 L+=['op -> erc [label=" ExpressRoute "];']
 if h['expressroute_gateway']:L+=['erc -> gw [label=" Private connectivity "];']
 if h['firewall'] and h['expressroute_gateway']:L+=['gw -> fw [label=" Hub routing "];']
 src='fw' if h['firewall'] else 'gw'
 flags=[]
 if p['allow_forwarded_traffic']:flags.append('Forwarded traffic')
 if p['allow_gateway_transit']:flags.append('Gateway transit')
 if p['use_remote_gateway']:flags.append('Remote gateway')
 lab='VNet Peering\\n'+' • '.join(flags)
 for i in range(1,len(sp)+1):L += [src+' -> sub'+str(i)+' [dir=both,label="'+lab+'",color="#1688f8"];']
 L+=['}']; return '\n'.join(L)
def drawio(m):
 def c(i,v,x,y,w,h,sty,parent='1'):return f'<mxCell id="{i}" value="{html.escape(v)}" style="{sty}" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
 R=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; h=m['hub']; op=m['onprem']; sp=m['spokes']
 R+=[c('op',op['name']+'&#xa;'+(op['cidr'] or 'CIDR not specified'),30,260,220,110,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f4f6f8;fontSize=14;'),c('erc','ExpressRoute Circuit',300,280,190,70,'shape=mxgraph.azure.express_route_circuits;html=1;verticalLabelPosition=bottom;verticalAlign=top;'),c('hub','Hub-VNet&#xa;'+(h['cidr'] or 'CIDR not specified'),540,80,390,520,'swimlane;rounded=1;html=1;startSize=50;container=1;collapsible=0;strokeColor=#1688f8;fillColor=#f4faff;')]
 R+=[c('gw','ExpressRoute Gateway',70,95,250,85,'shape=mxgraph.azure.virtual_network_gateways;html=1;verticalLabelPosition=bottom;verticalAlign=top;','hub'),c('fw','Azure Firewall',70,285,250,85,'shape=mxgraph.azure.firewalls;html=1;verticalLabelPosition=bottom;verticalAlign=top;','hub')]
 ys=[55,370]
 for i,s in enumerate(sp,1):
  sid='s'+str(i); R += [c(sid,s['name']+'&#xa;'+(s['cidr'] or 'CIDR not specified'),1010,ys[i-1],370,270,'swimlane;rounded=1;html=1;startSize=50;container=1;collapsible=0;strokeColor=#2e8b57;fillColor=#f5fff7;'),c('sub'+str(i),'Subnet&#xa;'+(s['subnet'] or 'CIDR not specified'),55,75,260,65,'rounded=1;whiteSpace=wrap;html=1;strokeColor=#82b6e8;dashed=1;','s'+str(i)),c('vm'+str(i),s['vm']+'&#xa;Windows Server',115,160,140,70,'shape=mxgraph.azure.virtual_machine;html=1;verticalLabelPosition=bottom;verticalAlign=top;','s'+str(i))]
 E=[('e1','op','erc','ExpressRoute'),('e2','erc','gw','Private connectivity'),('e3','gw','fw','Hub routing')]
 for i in range(1,len(sp)+1):E.append(('ep'+str(i),'fw','sub'+str(i),'VNet Peering | Gateway transit | Remote gateway'))
 for eid,a,b,l in E:R.append(f'<mxCell id="{eid}" value="{html.escape(l)}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#1688f8;strokeWidth=2;endArrow=block;" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="Azure Architecture"><mxGraphModel dx="1500" dy="850" grid="1" gridSize="10" page="1" pageWidth="1500" pageHeight="850"><root>'+''.join(R)+'</root></mxGraphModel></diagram></mxfile>'
def review(m):
 a=[]
 if m['hub']['firewall']:a.append('✓ Azure Firewall is centralised in the Hub VNet.')
 if m['expressroute']:a.append('✓ ExpressRoute private connectivity detected.')
 if m['peering']['allow_gateway_transit']:a.append('✓ Gateway transit detected on hub/spoke peering.')
 if m['peering']['use_remote_gateway']:a.append('✓ Spokes use the remote hub gateway.')
 if not m['onprem']['cidr']:a.append('ℹ On-premises CIDR was not supplied, so none was invented.')
 a.append('⚠ Add/validate UDRs if spoke and on-premises traffic must be forced through Azure Firewall.')
 return '\n'.join(a)
def render(m):
 open(MODEL,'w').write(json.dumps(m,indent=2)); d=os.path.join(OUT,'portal_v4.dot');open(d,'w').write(dot(m));open(DRAWIO,'w').write(drawio(m));subprocess.run(['dot','-Tpng',d,'-o',PNG],check=True,timeout=30)
HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Azure Architecture Studio</title><style>*{box-sizing:border-box}body{margin:0;font-family:Arial;background:#07111f;color:#e8f0ff}.top{height:66px;padding:0 22px;display:flex;align-items:center;justify-content:space-between;background:#0b1728;border-bottom:1px solid #20314a}.brand{font-size:20px;font-weight:800}.brand span{color:#39a8ff}.layout{display:grid;grid-template-columns:390px 1fr;min-height:calc(100vh - 66px)}.side{padding:18px;background:#0b1728;border-right:1px solid #20314a}.main{padding:18px}.card{background:#101f33;border:1px solid #263a55;border-radius:14px;padding:16px;margin-bottom:14px}textarea{width:100%;min-height:300px;background:#081522;color:white;border:1px solid #36506f;border-radius:10px;padding:13px}.refine{min-height:85px}.btn{border:0;border-radius:9px;padding:11px 14px;font-weight:700;background:#1688f8;color:white;margin:8px 6px 0 0;cursor:pointer}.btn2{background:#243c59;text-decoration:none;display:inline-block}.canvas{min-height:650px;background:white;border-radius:14px;display:flex;align-items:center;justify-content:center;overflow:auto;padding:16px}.canvas img{max-width:100%;height:auto}.muted{color:#94a9c3;font-size:13px}.review{white-space:pre-wrap;color:#cfe1f7}@media(max-width:850px){.layout{grid-template-columns:1fr}}</style></head><body><div class=top><div class=brand><span>Azure</span> Architecture Studio</div><div class=muted>Structured Azure renderer • Azure service icons • Editable Draw.io</div></div><div class=layout><aside class=side><div class=card><h3>Architecture requirement</h3><form method=post action=/generate><textarea name=requirements>{{req}}</textarea><button class=btn>Generate Diagram</button></form></div>{% if ready %}<div class=card><h3>Refine current diagram</h3><form method=post action=/refine><textarea class=refine name=refinement placeholder="Example: Add a third spoke"></textarea><button class=btn>Apply Changes</button></form></div><div class=card><h3>Architecture review</h3><div class=review>{{review}}</div></div>{% endif %}{% if error %}<div class=card>{{error}}</div>{% endif %}</aside><main class=main><div class=card><h3>Diagram preview</h3><div class=muted>Azure-style icon diagram generated from the requirement. PNG and Draw.io use the same architecture model.</div>{% if ready %}<a class="btn btn2" href=/png>Download PNG</a><a class="btn btn2" href=/drawio>Download Draw.io</a><a class="btn btn2" href=/model>Architecture JSON</a>{% endif %}</div><div class=canvas>{% if ready %}<img src="/png?t={{stamp}}">{% else %}<div style="color:#53677e">Enter a requirement to generate the architecture.</div>{% endif %}</div></main></div></body></html>'''
def page(req='',ready=False,error=None):return render_template_string(HTML,req=req,ready=ready,error=error,review=review(json.load(open(MODEL))) if ready and os.path.exists(MODEL) else '',stamp=time.time())
@app.get('/')
def home():return page()
@app.get('/health')
def health():return {'status':'ok','graphviz':bool(shutil.which('dot')),'azure_icons_found':len(ICONS),'mapped_icons':{k:bool(v) for k,v in ICONMAP.items()}}
@app.post('/generate')
def generate():
 req=request.form.get('requirements','').strip()
 if not req:return page(error='Please enter an architecture requirement.')
 try:m=interpret(req);render(m);return page(req,True)
 except Exception as e:return page(req,False,str(e))
@app.post('/refine')
def refine():
 if not os.path.exists(MODEL):return page(error='Generate a diagram first.')
 m=json.load(open(MODEL));r=request.form.get('refinement','').strip();low=r.lower()
 if 'third spoke' in low or 'spoke3' in low:
  c=re.findall(r'\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}',r);m['spokes'].append({'name':'Spoke3-VNet','cidr':c[0] if c else None,'subnet':c[1] if len(c)>1 else None,'vm':'VM03'})
 m['source']+='\nREFINEMENT: '+r;render(m);return page(m['source'],True)
@app.get('/png')
def png():return send_file(PNG,as_attachment=True,download_name='azure_architecture.png')
@app.get('/drawio')
def dio():return send_file(DRAWIO,as_attachment=True,download_name='azure_architecture.drawio')
@app.get('/model')
def mdl():return send_file(MODEL,as_attachment=True,download_name='architecture_model.json')
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','3000')))
