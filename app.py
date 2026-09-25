from flask import Flask, send_file, render_template_string, request
import os, subprocess, re, json, html, shutil
app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,"diagrams"); os.makedirs(OUT,exist_ok=True)
HTML='''<!doctype html><title>Arch Diagram Builder</title><style>body{font-family:Arial;margin:28px;background:#f5f7fb;color:#17233c;max-width:1200px}.card{background:white;padding:22px;border-radius:14px;margin-bottom:18px}textarea{width:100%;min-height:240px;padding:14px;box-sizing:border-box}button,a,select{padding:12px 16px;margin:8px 6px 8px 0;border-radius:8px}button,a{background:#1677ff;color:white;border:0;text-decoration:none;display:inline-block}pre{white-space:pre-wrap;background:#101827;color:#dce7ff;padding:16px;border-radius:10px;max-height:420px;overflow:auto}img{max-width:100%;border:1px solid #ddd;margin-top:15px}.error{background:#fff1f0;color:#a8071a;padding:14px;border-radius:8px}.ok{background:#f6ffed;color:#237804;padding:10px;border-radius:8px}</style><h1>Arch Diagram Builder</h1><p>Requirement → architecture model → generated Python → Graphviz → editable diagram</p><div class=card><form method=post action=/generate><h3>1. Describe your architecture</h3><textarea name=requirements placeholder="Example: Create an Azure landing zone with a firewall in a hub VNet and two spoke VNets, each containing two applications. Peer each spoke to the hub and route outbound traffic through the firewall.">{{req}}</textarea><h3>2. Output</h3><select name=format><option value=drawio>Draw.io (editable)</option><option value=visio>Visio (.vsdx)</option></select><br><button>Interpret & Generate</button></form></div>{% if error %}<div class="card error"><b>Generation error:</b> {{error}}</div>{% endif %}{% if ready %}<div class=card><div class=ok>Graphviz runtime detected. Diagram generated from the interpreted architecture model.</div><h3>Interpreted architecture</h3><pre>{{model}}</pre><h3>Generated Python</h3><pre>{{code}}</pre><a href=/python>Download Python</a><a href=/png>PNG preview</a><a href=/drawio>Editable Draw.io</a>{% if visio %}<p>Native VSDX is not yet generated; editable Draw.io is provided as the intermediate.</p>{% endif %}<br><img src="/png?t={{stamp}}"></div>{% endif %}'''

def count_phrase(t, noun, default=0):
 m=re.search(r'(\d+)\s+'+noun,t)
 if m:return int(m.group(1))
 words={"one":1,"two":2,"three":3,"four":4,"five":5,"six":6}
 for w,n in words.items():
  if re.search(r'\b'+w+r'\s+'+noun,t): return n
 return default

def interpret(text):
 t=text.lower(); containers=[]; nodes=[]; edges=[]; flows=[]
 def container(i,label,parent=None,kind="vnet"):
  if not any(x["id"]==i for x in containers): containers.append({"id":i,"label":label,"parent":parent,"kind":kind})
 def node(i,label,typ,parent=None):
  if not any(x["id"]==i for x in nodes): nodes.append({"id":i,"label":label,"type":typ,"parent":parent})
 def edge(a,b,label=""):
  if [a,b,label] not in edges: edges.append([a,b,label])
 azure='azure' in t or any(x in t for x in ['vnet','app service','key vault','front door'])
 root=None
 if azure:
  container("azure","Azure Architecture",None,"cloud"); root="azure"
 if 'landing zone' in t and azure: containers[0]['label']='Azure Landing Zone'
 hub=bool(re.search(r'\bhub\b',t))
 if hub:
  container("hub","Hub VNet",root)
  if 'firewall' in t:
   container("fwsubnet","AzureFirewallSubnet","hub","subnet"); node("firewall","Azure Firewall","firewall","fwsubnet")
  if 'bastion' in t:
   container("bastionsubnet","AzureBastionSubnet","hub","subnet"); node("bastion","Azure Bastion","bastion","bastionsubnet")
  if 'vpn gateway' in t or 'virtual network gateway' in t:
   container("gwsubnet","GatewaySubnet","hub","subnet"); node("vpn","VPN Gateway","vpn","gwsubnet")
 spoke_count=count_phrase(t,'spoke(?:s|\s+vnets?|\s+networks?)',0)
 numbered=[int(x) for x in re.findall(r'spoke(?:\s+network|\s+vnet)?\s*(\d+)',t)]
 if numbered: spoke_count=max(spoke_count,max(numbered))
 if 'spoke' in t and not spoke_count: spoke_count=1
 apps_each=1
 m=re.search(r'(\d+)\s+applications?.{0,40}(?:each|per)',t)
 if m: apps_each=int(m.group(1))
 else:
  words={"one":1,"two":2,"three":3,"four":4,"five":5}
  for w,n in words.items():
   if re.search(r'\b'+w+r'\s+applications?.{0,40}(?:each|per)',t): apps_each=n
 for s in range(1,spoke_count+1):
  sid=f"spoke{s}"; container(sid,f"Spoke VNet {s}",root)
  appsub=f"appsub{s}"; container(appsub,"Application Subnet",sid,"subnet")
  for a in range(1,apps_each+1): node(f"app{s}_{a}",f"Application {a}","app",appsub)
  if hub: edge("hub",sid,"VNet Peering")
 # Generic tier/subnet interpretation, useful for detailed Contoso-style requirements.
 tiers=[('frontend','Frontend Subnet'),('backend','Backend Subnet'),('data','Data Subnet')]
 for key,label in tiers:
  if key+' subnet' in t:
   parent='hub' if hub and key=='frontend' else root
   container(key+'subnet',label,parent,'subnet')
 # Shared/application services
 placement=root
 if 'front door' in t: node('frontdoor','Azure Front Door','frontdoor',root)
 if 'application gateway' in t or re.search(r'\bwaf\b',t): node('appgw','Application Gateway / WAF','appgw','frontendsubnet' if any(c['id']=='frontendsubnet' for c in containers) else root)
 if 'app service' in t or 'web app' in t: node('webapp','App Service','app','backendsubnet' if any(c['id']=='backendsubnet' for c in containers) else placement)
 if 'function app' in t or 'azure function' in t: node('function','Function App','function','backendsubnet' if any(c['id']=='backendsubnet' for c in containers) else placement)
 if 'service bus' in t: node('servicebus','Service Bus','servicebus',placement)
 if 'key vault' in t: node('keyvault','Azure Key Vault','keyvault','datasubnet' if any(c['id']=='datasubnet' for c in containers) else placement)
 if 'sql' in t: node('sql','Azure SQL','sql','datasubnet' if any(c['id']=='datasubnet' for c in containers) else placement)
 if 'storage' in t or 'blob' in t: node('storage','Azure Storage','storage','datasubnet' if any(c['id']=='datasubnet' for c in containers) else placement)
 if 'log analytics' in t: node('logs','Log Analytics','monitor',root)
 if 'application insights' in t or 'monitor' in t: node('monitor','Application Insights / Monitor','monitor',root)
 # Explicit common traffic flows rather than only drawing resource inventory.
 ids={n['id'] for n in nodes}
 if {'frontdoor','appgw'}<=ids: edge('frontdoor','appgw','HTTPS')
 if {'appgw','webapp'}<=ids: edge('appgw','webapp','HTTPS')
 if {'webapp','sql'}<=ids: edge('webapp','sql','Private access' if 'private endpoint' in t else 'Data')
 if {'webapp','storage'}<=ids: edge('webapp','storage','Private access' if 'private endpoint' in t else 'Data')
 if {'function','servicebus'}<=ids: edge('function','servicebus','Messaging')
 if {'webapp','keyvault'}<=ids: edge('webapp','keyvault','Secrets')
 if 'outbound' in t and 'firewall' in ids: flows.append('Outbound traffic routed through Azure Firewall')
 return {"provider":"Azure" if azure else "Cloud","source_requirement":text,"containers":containers,"nodes":nodes,"edges":edges,"traffic_notes":flows,"layout":{"direction":"TB" if any(x in t for x in ['top','below','bottom']) else "LR"}}

def pycode(model):
 imports='''from diagrams import Diagram, Cluster, Edge\nfrom diagrams.azure.network import Firewall, VirtualNetworks, VirtualNetworkGateways, ApplicationGateways, FrontDoors\nfrom diagrams.azure.compute import AppServices, FunctionApps\nfrom diagrams.azure.integration import ServiceBus\nfrom diagrams.azure.security import KeyVaults\nfrom diagrams.azure.database import SQLDatabases\nfrom diagrams.azure.storage import StorageAccounts\nfrom diagrams.azure.devops import ApplicationInsights\nfrom diagrams.azure.analytics import LogAnalyticsWorkspaces\n'''
 cls={"firewall":"Firewall","app":"AppServices","function":"FunctionApps","servicebus":"ServiceBus","frontdoor":"FrontDoors","appgw":"ApplicationGateways","keyvault":"KeyVaults","sql":"SQLDatabases","storage":"StorageAccounts","monitor":"ApplicationInsights","bastion":"VirtualNetworks","vpn":"VirtualNetworkGateways"}
 containers={x['id']:x for x in model['containers']}; children={}; nodechildren={}
 for c in model['containers']: children.setdefault(c.get('parent'),[]).append(c)
 for n in model['nodes']: nodechildren.setdefault(n.get('parent'),[]).append(n)
 direction=model.get('layout',{}).get('direction','LR')
 lines=[imports,f'with Diagram("Generated Architecture", filename="diagrams/generated_architecture", outformat="png", show=False, direction="{direction}", graph_attr={{"compound":"true","splines":"ortho","nodesep":"0.7","ranksep":"0.9"}}):','    n = {}','    anchors = {}']
 def emit(parent,indent):
  for n in nodechildren.get(parent,[]):
   klass='LogAnalyticsWorkspaces' if n['id']=='logs' else cls.get(n['type'],'AppServices')
   lines.append(' '*indent+f'n["{n["id"]}"] = {klass}("{n["label"]}")')
  for c in children.get(parent,[]):
   lines.append(' '*indent+f'with Cluster("{c["label"]}"):')
   lines.append(' '*(indent+4)+f'anchors["{c["id"]}"] = VirtualNetworks("")')
   emit(c['id'],indent+4)
 emit(None,4)
 nodeids={n['id'] for n in model['nodes']}
 containerids={c['id'] for c in model['containers']}
 def ref(x): return f'n["{x}"]' if x in nodeids else f'anchors["{x}"]'
 for a,b,label in model['edges']:
  if a in nodeids|containerids and b in nodeids|containerids: lines.append(f'    {ref(a)} >> Edge(label="{label}") >> {ref(b)}')
 return '\n'.join(lines)+'\n'

def drawio_xml(model):
 esc=lambda s: html.escape(str(s),quote=True)
 cells=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; children={}; nodechildren={}
 for c in model['containers']: children.setdefault(c.get('parent'),[]).append(c)
 for n in model['nodes']: nodechildren.setdefault(n.get('parent'),[]).append(n)
 def size(cid):
  cc=children.get(cid,[]); nn=nodechildren.get(cid,[])
  if not cc:return (320,max(160,90+90*len(nn)))
  ss=[size(x['id']) for x in cc];return (max(400,max([w for w,h in ss],default=320)+60),90+sum(h for w,h in ss)+30*max(0,len(ss)-1)+90*len(nn))
 def emit(parent,parentcell,x,y):
  cy=40
  for c in children.get(parent,[]):
   w,h=size(c['id']); cells.append(f'<mxCell id="{c["id"]}" value="{esc(c["label"])}" style="swimlane;html=1;rounded=1;startSize=32;horizontal=1;container=1;collapsible=0;" vertex="1" parent="{parentcell}"><mxGeometry x="{x}" y="{y+cy}" width="{w}" height="{h}" as="geometry"/></mxCell>'); emit(c['id'],c['id'],20,10); cy+=h+30
  ny=50
  for n in nodechildren.get(parent,[]): cells.append(f'<mxCell id="{n["id"]}" value="{esc(n["label"])}" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="{parentcell}"><mxGeometry x="40" y="{ny}" width="200" height="60" as="geometry"/></mxCell>'); ny+=80
 emit(None,'1',20,10)
 for i,(a,b,label) in enumerate(model['edges']): cells.append(f'<mxCell id="e{i}" value="{esc(label)}" edge="1" parent="1" source="{a}" target="{b}" style="edgeStyle=orthogonalEdgeStyle;endArrow=block;html=1;"><mxGeometry relative="1" as="geometry"/></mxCell>')
 return '<mxfile><diagram name="Architecture"><mxGraphModel><root>'+''.join(cells)+'</root></mxGraphModel></diagram></mxfile>'

def graphviz_check():
 dot=shutil.which('dot')
 if not dot:return False,'Graphviz executable `dot` is not installed in the runtime. Install the Graphviz system package, not only the Python dependency.'
 try:
  p=subprocess.run([dot,'-V'],capture_output=True,text=True,timeout=5); return p.returncode==0,(p.stderr or p.stdout).strip()
 except Exception as e:return False,str(e)

@app.get("/")
def home(): return render_template_string(HTML,req="",ready=False,error=None)
@app.get('/health')
def health():
 ok,detail=graphviz_check(); return {"status":"ok" if ok else "error","graphviz":detail},200 if ok else 500
@app.post("/generate")
def generate():
 req=request.form.get("requirements","").strip(); fmt=request.form.get("format","drawio")
 if not req:return render_template_string(HTML,req=req,ready=False,error='Please describe the architecture first.')
 ok,detail=graphviz_check()
 if not ok:return render_template_string(HTML,req=req,ready=False,error=detail)
 model=interpret(req); code=pycode(model)
 open(os.path.join(BASE,"last_requirement.txt"),"w").write(req); open(os.path.join(BASE,"architecture_model.json"),"w").write(json.dumps(model,indent=2)); p=os.path.join(BASE,"generated_architecture.py"); open(p,"w").write(code)
 try: subprocess.run(["python",p],cwd=BASE,check=True,timeout=30,capture_output=True,text=True)
 except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
  detail=(getattr(e,"stderr",None) or getattr(e,"stdout",None) or str(e))[-3000:]; return render_template_string(HTML,req=req,ready=False,error=detail)
 open(os.path.join(OUT,"generated_architecture.drawio"),"w").write(drawio_xml(model))
 return render_template_string(HTML,req=req,ready=True,error=None,model=json.dumps(model,indent=2),code=code,visio=fmt=="visio",stamp=os.path.getmtime(p))
@app.get("/python")
def python_file(): return send_file(os.path.join(BASE,"generated_architecture.py"),as_attachment=True,download_name="generated_architecture.py")
@app.get("/png")
def png(): return send_file(os.path.join(OUT,"generated_architecture.png"),mimetype="image/png")
@app.get("/drawio")
def drawio(): return send_file(os.path.join(OUT,"generated_architecture.drawio"),as_attachment=True,download_name="generated_architecture.drawio")
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","3000")))
