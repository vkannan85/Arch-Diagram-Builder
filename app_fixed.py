from app import app, interpret, drawio_xml, graphviz_check, BASE, OUT
import os, subprocess

def pycode(model):
    imports = '''from diagrams import Diagram, Cluster, Edge\nfrom diagrams.azure.network import Firewall, VirtualNetworks, VirtualNetworkGateways, ApplicationGateway, FrontDoors\nfrom diagrams.azure.compute import AppServices, FunctionApps\nfrom diagrams.azure.integration import ServiceBus\nfrom diagrams.azure.security import KeyVaults\nfrom diagrams.azure.database import SQLDatabases\nfrom diagrams.azure.storage import StorageAccounts\nfrom diagrams.azure.devops import ApplicationInsights\n'''
    cls={"firewall":"Firewall","app":"AppServices","function":"FunctionApps","servicebus":"ServiceBus","frontdoor":"FrontDoors","appgw":"ApplicationGateway","keyvault":"KeyVaults","sql":"SQLDatabases","storage":"StorageAccounts","monitor":"ApplicationInsights","bastion":"VirtualNetworks","vpn":"VirtualNetworkGateways"}
    children={}; nodechildren={}
    for c in model['containers']: children.setdefault(c.get('parent'),[]).append(c)
    for n in model['nodes']: nodechildren.setdefault(n.get('parent'),[]).append(n)
    direction=model.get('layout',{}).get('direction','LR')
    lines=[imports,f'with Diagram("Generated Architecture", filename="diagrams/generated_architecture", outformat="png", show=False, direction="{direction}", graph_attr={{"compound":"true","splines":"ortho","nodesep":"0.7","ranksep":"0.9"}}):','    n = {}','    anchors = {}']
    def emit(parent,indent):
        for n in nodechildren.get(parent,[]):
            lines.append(' '*indent+f'n["{n["id"]}"] = {cls.get(n["type"],"AppServices")}("{n["label"]}")')
        for c in children.get(parent,[]):
            lines.append(' '*indent+f'with Cluster("{c["label"]}"):')
            lines.append(' '*(indent+4)+f'anchors["{c["id"]}"] = VirtualNetworks("")')
            emit(c['id'],indent+4)
    emit(None,4)
    nodeids={n['id'] for n in model['nodes']}; containerids={c['id'] for c in model['containers']}
    def ref(x): return f'n["{x}"]' if x in nodeids else f'anchors["{x}"]'
    for a,b,label in model['edges']:
        if a in nodeids|containerids and b in nodeids|containerids:
            lines.append(f'    {ref(a)} >> Edge(label="{label}") >> {ref(b)}')
    return '\n'.join(lines)+'\n'

app.view_functions['generate'].__globals__['pycode']=pycode

CONTOSO='''Create an Azure architecture for Contoso with one VNet containing a frontend subnet, backend subnet and data subnet. Use Azure Front Door, Application Gateway WAF, App Service web app, Function App, Service Bus, Azure SQL Database, Storage Account, Key Vault with private endpoints, Log Analytics and Application Insights. Users access Front Door then Application Gateway then the web app. The web app accesses SQL, Storage and Key Vault. The Function App uses Service Bus. Show monitoring and place data services in the data subnet.'''

def run_contoso():
    ok,detail=graphviz_check()
    if not ok:return {"status":"failed","stage":"graphviz","error":detail},500
    try:
        model=interpret(CONTOSO); code=pycode(model); p=os.path.join(BASE,'regression_contoso_generated.py'); open(p,'w').write(code)
        run=subprocess.run(['python',p],cwd=BASE,capture_output=True,text=True,timeout=30)
        png=os.path.join(OUT,'generated_architecture.png')
        if run.returncode!=0:return {"status":"failed","stage":"python","stderr":run.stderr[-3000:]},500
        drawio=os.path.join(OUT,'regression_contoso.drawio'); open(drawio,'w').write(drawio_xml(model))
        if not os.path.exists(png) or os.path.getsize(png)==0 or not os.path.exists(drawio):return {"status":"failed","stage":"artifacts"},500
        return {"status":"passed","graphviz":detail,"png_exists":True,"png_bytes":os.path.getsize(png),"drawio_exists":True,"nodes":len(model['nodes']),"containers":len(model['containers']),"edges":len(model['edges'])},200
    except Exception as e:return {"status":"failed","stage":"exception","error":repr(e)},500

@app.get('/regression/contoso')
def regression_contoso(): return run_contoso()

# Railway's existing /health path now performs the full Contoso regression.
# A SUCCESS deployment therefore proves Python + Graphviz + PNG + Draw.io.
def regression_health(): return run_contoso()
app.view_functions['health']=regression_health
