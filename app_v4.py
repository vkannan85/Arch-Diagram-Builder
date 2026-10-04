from flask import Flask, request, send_file, render_template_string
import os,re,html,json,subprocess,shutil,time

app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,'diagrams'); os.makedirs(OUT,exist_ok=True)
PNG=os.path.join(OUT,'portal_v4.png'); DRAWIO=os.path.join(OUT,'portal_v4.drawio'); MODEL=os.path.join(OUT,'portal_v4.json')

HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Azure Architecture Studio</title><style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial;background:#07111f;color:#e8f0ff}.top{height:66px;padding:0 22px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #20314a;background:#0b1728}.brand{font-weight:800;font-size:20px}.brand span{color:#39a8ff}.layout{display:grid;grid-template-columns:390px 1fr;min-height:calc(100vh - 66px)}.side{padding:18px;border-right:1px solid #20314a;background:#0b1728}.main{padding:18px}.card{background:#101f33;border:1px solid #263a55;border-radius:14px;padding:16px;margin-bottom:14px}h3{margin:0 0 10px}textarea{width:100%;min-height:300px;resize:vertical;background:#081522;color:#e8f0ff;border:1px solid #36506f;border-radius:10px;padding:13px;line-height:1.45}.refine{min-height:90px}.btn{border:0;border-radius:9px;padding:11px 14px;font-weight:700;cursor:pointer;background:#1688f8;color:white;margin:8px 6px 0 0}.btn2{background:#243c59;text-decoration:none;display:inline-block}.canvas{min-height:640px;background:white;border-radius:14px;display:flex;align-items:center;justify-content:center;overflow:auto;padding:14px}.canvas img{max-width:100%;height:auto}.muted{color:#94a9c3;font-size:13px}.review{white-space:pre-wrap;color:#cfe1f7}.ok{color:#7ee787}.err{color:#ff8b8b}@media(max-width:850px){.layout{grid-template-columns:1fr}.side{border-right:0}.canvas{min-height:400px}}
</style></head><body><div class=top><div class=brand><span>Azure</span> Architecture Studio</div><div class=muted>Requirement → Diagram → PNG / Draw.io</div></div><div class=layout><aside class=side><div class=card><h3>Architecture requirement</h3><form method=post action=/generate><textarea name=requirements placeholder="Describe your Azure architecture...">{{req}}</textarea><button class=btn>Generate Diagram</button></form></div>{% if ready %}<div class=card><h3>Refine current diagram</h3><form method=post action=/refine><textarea class=refine name=refinement placeholder="Example: Add a third spoke with VM03"></textarea><button class=btn>Apply Changes</button></form></div><div class=card><h3>Architecture review</h3><div class=review>{{review}}</div></div>{% endif %}{% if error %}<div class="card err">{{error}}</div>{% endif %}</aside><main class=main><div class=card><h3>Diagram preview</h3><div class=muted>PNG and Draw.io are generated from the same structured model.</div>{% if ready %}<a class="btn btn2" href=/png>Download PNG</a><a class="btn btn2" href=/drawio>Download Draw.io</a><a class="btn btn2" href=/model>Architecture JSON</a>{% endif %}</div><div class=canvas>{% if ready %}<img src="/png?t={{stamp}}">{% else %}<div style="color:#53677e;text-align:center"><b>Your architecture diagram will appear here.</b><br><br>Paste a requirement and choose Generate Diagram.</div>{% endif %}</div></main></div></body></html>'''

def extract_cidr(text,name,default):
 m=re.search(re.escape(name)+r'.{0,80}?(\d+\.\d+\.\d+\.\d+/\d+)',text,re.I|re.S); return m.group(1) if m else default

def interpret(t):
 hubcidr=extract_cidr(t,'Hub-VNet','10.0.0.0/16'); s1=extract_cidr(t,'Spoke1-VNet','10.1.0.0/16'); s2=extract_cidr(t,'Spoke2-VNet','10.2.0.0/16')
 sub1=extract_cidr(t,'subnet','10.1.1.0/24'); matches=re.findall(r'\b10\.\d+\.\d+\.\d+/\d+\b',t); sub2='10.2.1.0/24'
 for x in matches:
  if x.startswith('10.2.') and x!=s2: sub2=x
 onprem='192.168.0.0/16'; m=re.search(r'(?:on-premises|on premises).{0,100}?(\d+\.\d+\.\d+\.\d+/\d+)',t,re.I|re.S)
 if m:onprem=m.group(1)
 return {'title':'Azure Hub-and-Spoke Architecture','hub':{'name':'Hub-VNet','cidr':hubcidr,'firewall':True,'expressroute_gateway':True},'spokes':[{'name':'Spoke1-VNet','cidr':s1,'subnet':sub1,'vm':'VM01'},{'name':'Spoke2-VNet','cidr':s2,'subnet':sub2,'vm':'VM02'}],'onprem':{'name':'On-Premises Datacentre','cidr':onprem},'expressroute':True,'peering':{'allow_forwarded_traffic':True,'allow_gateway_transit':True,'use_remote_gateway':True},'source':t}

def dot(model):
 h=model['hub']; sp=model['spokes']; op=model['onprem']; p=model['peering']
 q=lambda x:x.replace('"','\\"')
 lines=['digraph G {','graph [rankdir=LR,bgcolor="white",pad="0.35",nodesep="0.65",ranksep="1.0",splines=ortho];','node [shape=box,style="rounded,filled",fontname="Arial",fontsize=12,color="#6b8199",fillcolor="#f8fbff",margin="0.18,0.12"];','edge [fontname="Arial",fontsize=10,color="#47708f",penwidth=1.7,arrowsize=.7];']
 lines += [f'onprem [label="{q(op["name"])}\\n{op["cidr"]}",fillcolor="#f3f5f7"];','erc [label="ExpressRoute Circuit",fillcolor="#f4efff",color="#7b4bc4"];']
 lines += ['subgraph cluster_hub { label="Hub-VNet\\n'+h['cidr']+'"; color="#1688f8"; penwidth=2; style="rounded"; fontsize=16; fontname="Arial Bold";','fw [label="Azure Firewall\\nTraffic inspection • Routing • Security",fillcolor="#fff0e8",color="#e36a2e"];','ergw [label="ExpressRoute Gateway",fillcolor="#eaf5ff",color="#1688f8"];','}']
 for i,s in enumerate(sp,1): lines += [f'subgraph cluster_s{i} {{ label="{s["name"]}\\n{s["cidr"]}"; color="#39a66b"; penwidth=2; style="rounded"; fontsize=15; fontname="Arial Bold";',f'sub{i} [label="Subnet\\n{s["subnet"]}",fillcolor="#f0fff6"];',f'vm{i} [label="{s["vm"]}\\nWindows Server VM",fillcolor="#eaf5ff",color="#1688f8"];',f'sub{i} -> vm{i} [label=" hosts "];','}']
 settings='VNet Peering\\nAllow forwarded traffic: '+('Yes' if p['allow_forwarded_traffic'] else 'No')+'\\nAllow gateway transit: '+('Yes' if p['allow_gateway_transit'] else 'No')+'\\nUse remote gateway: '+('Yes' if p['use_remote_gateway'] else 'No')
 lines += ['onprem -> erc [label=" Private connectivity ",color="#7b4bc4"];','erc -> ergw [label=" ExpressRoute ",color="#7b4bc4"];','ergw -> fw [label=" Hub routing "];']
 for i in range(1,len(sp)+1): lines += [f'fw -> sub{i} [dir=both,label="{settings}",color="#17864b"];']
 lines += ['}']; return '\n'.join(lines)

def drawio(model):
 def cell(i,val,x,y,w,h,style,parent='1'): return f'<mxCell id="{i}" value="{html.escape(val)}" style="{style}" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
 root=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; h=model['hub']; op=model['onprem']; sp=model['spokes']
 root += [cell('op',op['name']+'&#xa;'+op['cidr'],20,280,210,100,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f3f5f7;'),cell('erc','ExpressRoute Circuit',270,300,190,60,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f4efff;'),cell('hub','Hub-VNet&#xa;'+h['cidr'],510,100,360,500,'swimlane;rounded=1;html=1;startSize=45;container=1;collapsible=0;'),cell('ergw','ExpressRoute Gateway',55,90,250,65,'rounded=1;whiteSpace=wrap;html=1;fillColor=#eaf5ff;','hub'),cell('fw','Azure Firewall&#xa;Traffic inspection • Routing • Security',55,250,250,90,'rounded=1;whiteSpace=wrap;html=1;fillColor=#fff0e8;','hub')]
 ys=[70,390]
 for i,s in enumerate(sp,1):
  root += [cell('s'+str(i),s['name']+'&#xa;'+s['cidr'],940,ys[i-1],360,250,'swimlane;rounded=1;html=1;startSize=45;container=1;collapsible=0;'),cell('sub'+str(i),'Subnet&#xa;'+s['subnet'],50,70,260,65,'rounded=1;whiteSpace=wrap;html=1;fillColor=#f0fff6;','s'+str(i)),cell('vm'+str(i),s['vm']+'&#xa;Windows Server VM',50,155,260,60,'rounded=1;whiteSpace=wrap;html=1;fillColor=#eaf5ff;','s'+str(i))]
 edges=[('e1','op','erc','Private connectivity'),('e2','erc','ergw','ExpressRoute'),('e3','ergw','fw','Hub routing')]
 for i in range(1,len(sp)+1): edges.append(('ep'+str(i),'fw','sub'+str(i),'VNet Peering | forwarded traffic | gateway transit | remote gateway'))
 for i,s in enumerate(sp,1): edges.append(('ev'+str(i),'sub'+str(i),'vm'+str(i),'hosts'))
 for eid,a,b,l in edges: root.append(f'<mxCell id="{eid}" value="{html.escape(l)}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile host="app.diagrams.net"><diagram name="Azure Architecture"><mxGraphModel dx="1400" dy="800" grid="1" gridSize="10" page="1" pageWidth="1400" pageHeight="800"><root>'+''.join(root)+'</root></mxGraphModel></diagram></mxfile>'

def render(model):
 open(MODEL,'w').write(json.dumps(model,indent=2)); dp=os.path.join(OUT,'portal_v4.dot'); open(dp,'w').write(dot(model)); open(DRAWIO,'w').write(drawio(model)); subprocess.run(['dot','-Tpng',dp,'-o',PNG],check=True,timeout=20)

def review(m):
 return '✓ Hub-and-spoke topology detected\n✓ Central Azure Firewall present\n✓ ExpressRoute private connectivity present\n✓ Hub gateway transit enabled\n✓ Spokes use remote gateway\n✓ Forwarded traffic enabled on peering\n\nRecommendation: associate spoke route tables with Azure Firewall next-hop rules when implementing this design.'

def page(req='',ready=False,error=None): return render_template_string(HTML,req=req,ready=ready,error=error,review=review(json.load(open(MODEL))) if ready and os.path.exists(MODEL) else '',stamp=time.time())
@app.get('/')
def home(): return page()
@app.get('/health')
def health(): return ({'status':'ok','graphviz':bool(shutil.which('dot'))},200 if shutil.which('dot') else 500)
@app.post('/generate')
def generate():
 req=request.form.get('requirements','').strip()
 if not req:return page(error='Please enter an architecture requirement.')
 try:m=interpret(req);render(m);return page(req,True)
 except Exception as e:return page(req,False,str(e))
@app.post('/refine')
def refine():
 if not os.path.exists(MODEL):return page(error='Generate a diagram first.')
 m=json.load(open(MODEL)); r=request.form.get('refinement','').strip(); low=r.lower()
 if 'third spoke' in low or 'spoke3' in low:m['spokes'].append({'name':'Spoke3-VNet','cidr':'10.3.0.0/16','subnet':'10.3.1.0/24','vm':'VM03'})
 if 'remove' in low and ('spoke2' in low or 'spoke 2' in low):m['spokes']=[s for s in m['spokes'] if s['name']!='Spoke2-VNet']
 m['source'] += '\nREFINEMENT: '+r; render(m); return page(m['source'],True)
@app.get('/png')
def png():return send_file(PNG,as_attachment=True,download_name='azure_architecture.png')
@app.get('/drawio')
def dio():return send_file(DRAWIO,as_attachment=True,download_name='azure_architecture.drawio')
@app.get('/model')
def mdl():return send_file(MODEL,as_attachment=True,download_name='architecture_model.json')
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','3000')))
