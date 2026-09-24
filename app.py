from flask import Flask, send_file, render_template_string, request
import os, subprocess, re, json
app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,"diagrams"); os.makedirs(OUT,exist_ok=True)
HTML='''<!doctype html><title>Arch Diagram Builder</title><style>body{font-family:Arial;margin:28px;background:#f5f7fb;color:#17233c;max-width:1200px}.card{background:white;padding:22px;border-radius:14px;margin-bottom:18px}textarea{width:100%;min-height:240px;padding:14px;box-sizing:border-box}button,a,select{padding:12px 16px;margin:8px 6px 8px 0;border-radius:8px}button,a{background:#1677ff;color:white;border:0;text-decoration:none;display:inline-block}pre{white-space:pre-wrap;background:#101827;color:#dce7ff;padding:16px;border-radius:10px;max-height:420px;overflow:auto}img{max-width:100%;border:1px solid #ddd;margin-top:15px}</style>
<h1>Arch Diagram Builder</h1><p>Natural language → architecture model → generated Python → GraphViz → editable diagram</p>
<div class=card><form method=post action=/generate><h3>1. Describe your architecture</h3><textarea name=requirements placeholder="Write paragraphs, bullet points or connections. Example: Create an Azure landing zone with a firewall in the hub network and two spoke networks, each containing two applications.">{{req}}</textarea><h3>2. Output</h3><select name=format><option value=drawio>Draw.io (editable)</option><option value=visio>Visio (.vsdx)</option></select><br><button>Generate from requirement</button></form></div>
{% if ready %}<div class=card><h3>Interpreted architecture</h3><pre>{{model}}</pre><h3>Generated Python</h3><pre>{{code}}</pre><a href=/python>Download Python</a><a href=/png>PNG preview</a><a href=/drawio>Editable Draw.io</a>{% if visio %}<p>Native VSDX is not yet generated; editable Draw.io is provided as the intermediate.</p>{% endif %}<br><img src="/png?t={{stamp}}"></div>{% endif %}'''
def interpret(text):
 t=text.lower(); nodes=[]; edges=[]; groups=[]
 def add(i,label,typ,group=None):
  if not any(x["id"]==i for x in nodes): nodes.append({"id":i,"label":label,"type":typ,"group":group})
 hub=bool(re.search(r'\bhub\b',t)); spokes=re.findall(r'(?:spoke(?:\s+network|\s+vnet)?\s*(\d+))',t)
 spoke_count=max([int(x) for x in spokes],default=0)
 m=re.search(r'(\d+)\s+spoke',t)
 if m: spoke_count=max(spoke_count,int(m.group(1)))
 if 'spoke' in t and spoke_count==0: spoke_count=2 if re.search(r'(two|2).*spoke',t) else 1
 if hub:
  groups.append("Hub VNet"); add("hub","Hub VNet","vnet")
 if 'firewall' in t:
  add("firewall","Azure Firewall","firewall","Hub VNet" if hub else None)
  if hub: edges.append(("hub","firewall"))
 apps_each=2 if re.search(r'(two|2)\s+applications?.*(each|per)|each.*(two|2)\s+applications?',t) else 1
 for s in range(1,spoke_count+1):
  g=f"Spoke VNet {s}"; groups.append(g); sid=f"spoke{s}"; add(sid,g,"vnet")
  if hub: edges.append(("hub",sid))
  if 'firewall' in t: edges.append(("firewall",sid))
  for a in range(1,apps_each+1):
   aid=f"app{s}_{a}"; add(aid,f"Application {a}","app",g); edges.append((sid,aid))
 # common Azure services
 defs=[('key vault','keyvault','Azure Key Vault','keyvault'),('sql','sql','Azure SQL','sql'),('storage','storage','Azure Storage','storage'),('monitor','monitor','Azure Monitor','monitor'),('bastion','bastion','Azure Bastion','bastion'),('vpn gateway','vpn','VPN Gateway','vpn')]
 for key,i,l,typ in defs:
  if key in t: add(i,l,typ)
 # explicit arrows
 for a,b in re.findall(r'([^\n;]+?)\s*->\s*([^\n;]+)',text):
  pass
 return {"provider":"Azure" if 'azure' in t else "Cloud","groups":groups,"nodes":nodes,"edges":edges}
def pycode(model):
 nodes=model["nodes"]; edges=model["edges"]
 imports='''from diagrams import Diagram, Cluster, Edge
from diagrams.azure.network import Firewall, VirtualNetworks
from diagrams.azure.compute import AppServices
from diagrams.azure.security import KeyVaults
from diagrams.azure.database import SQLDatabases
from diagrams.azure.storage import StorageAccounts
from diagrams.azure.devops import ApplicationInsights
from diagrams.azure.network import Bastion, VirtualNetworkGateways
'''
 cls={"vnet":"VirtualNetworks","firewall":"Firewall","app":"AppServices","keyvault":"KeyVaults","sql":"SQLDatabases","storage":"StorageAccounts","monitor":"ApplicationInsights","bastion":"Bastion","vpn":"VirtualNetworkGateways"}
 lines=[imports,'with Diagram("Generated Architecture", filename="diagrams/generated_architecture", outformat="png", show=False, direction="LR"):', '    n = {}']
 grouped={}
 for x in nodes:
  grouped.setdefault(x.get("group"),[]).append(x)
 for x in grouped.get(None,[]):
  lines.append(f'    n["{x["id"]}"] = {cls.get(x["type"],"AppServices")}("{x["label"]}")')
 for g,xs in grouped.items():
  if not g: continue
  lines.append(f'    with Cluster("{g}"):')
  for x in xs: lines.append(f'        n["{x["id"]}"] = {cls.get(x["type"],"AppServices")}("{x["label"]}")')
 for a,b in edges: lines.append(f'    n["{a}"] >> n["{b}"]')
 lines.append('')
 return "\n".join(lines)
@app.get("/")
def home(): return render_template_string(HTML,req="",ready=False)
@app.post("/generate")
def generate():
 req=request.form.get("requirements","").strip(); fmt=request.form.get("format","drawio")
 model=interpret(req); code=pycode(model)
 open(os.path.join(BASE,"last_requirement.txt"),"w").write(req)
 open(os.path.join(BASE,"architecture_model.json"),"w").write(json.dumps(model,indent=2))
 p=os.path.join(BASE,"generated_architecture.py"); open(p,"w").write(code)
 subprocess.run(["python",p],cwd=BASE,check=True,timeout=30)
 dot=os.path.join(OUT,"generated_architecture.dot")
 # diagrams normally removes DOT; regenerate through graphviz source is not guaranteed, so use existing PNG and optional conversion path
 drawio=os.path.join(OUT,"generated_architecture.drawio")
 # Generate a basic editable draw.io model directly from structured architecture
 cells=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; pos={}
 for idx,x in enumerate(model["nodes"]):
  xx=60+(idx%4)*220; yy=80+(idx//4)*130; pos[x["id"]]=(xx,yy)
  cells.append(f'<mxCell id="{x["id"]}" value="{x["label"]}" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="{xx}" y="{yy}" width="160" height="70" as="geometry"/></mxCell>')
 for i,(a,b) in enumerate(model["edges"]): cells.append(f'<mxCell id="e{i}" edge="1" parent="1" source="{a}" target="{b}" style="edgeStyle=orthogonalEdgeStyle;endArrow=block;"><mxGeometry relative="1" as="geometry"/></mxCell>')
 xml='<mxfile><diagram name="Architecture"><mxGraphModel><root>'+''.join(cells)+'</root></mxGraphModel></diagram></mxfile>'
 open(drawio,"w").write(xml)
 return render_template_string(HTML,req=req,ready=True,model=json.dumps(model,indent=2),code=code,visio=fmt=="visio",stamp=os.path.getmtime(p))
@app.get("/python")
def python_file(): return send_file(os.path.join(BASE,"generated_architecture.py"),as_attachment=True,download_name="generated_architecture.py")
@app.get("/png")
def png(): return send_file(os.path.join(OUT,"generated_architecture.png"),mimetype="image/png")
@app.get("/drawio")
def drawio(): return send_file(os.path.join(OUT,"generated_architecture.drawio"),as_attachment=True,download_name="generated_architecture.drawio")
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","3000")))
