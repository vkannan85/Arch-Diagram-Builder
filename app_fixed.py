from app import app, drawio_xml, graphviz_check, BASE, OUT
import os, subprocess, re, json

# Production interpreter: natural language -> structured architecture model.
def interpret(text):
    t=text.lower(); containers=[]; nodes=[]; edges=[]; notes=[]
    def container(i,label,parent=None,kind='vnet'):
        if not any(x['id']==i for x in containers): containers.append({'id':i,'label':label,'parent':parent,'kind':kind})
    def node(i,label,typ,parent=None):
        if not any(x['id']==i for x in nodes): nodes.append({'id':i,'label':label,'type':typ,'parent':parent})
    def edge(a,b,label=''):
        if [a,b,label] not in edges: edges.append([a,b,label])
    def has(*words): return any(w in t for w in words)
    def num(pattern, default=0):
        m=re.search(r'(\d+)\s+'+pattern,t)
        if m:return int(m.group(1))
        words={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8}
        for w,n in words.items():
            if re.search(r'\b'+w+r'\s+'+pattern,t):return n
        return default

    azure=has('azure','vnet','app service','key vault','front door','service bus','application gateway')
    root='azure' if azure else 'cloud'; container(root,'Azure Architecture' if azure else 'Cloud Architecture',None,'cloud')
    if 'landing zone' in t: containers[0]['label']='Azure Landing Zone'

    hub=bool(re.search(r'\bhub\b',t))
    if hub:
        container('hub','Hub VNet',root)
        if has('firewall'): container('fwsubnet','AzureFirewallSubnet','hub','subnet'); node('firewall','Azure Firewall','firewall','fwsubnet')
        if has('bastion'): container('bastionsubnet','AzureBastionSubnet','hub','subnet'); node('bastion','Azure Bastion','bastion','bastionsubnet')
        if has('vpn gateway','virtual network gateway','expressroute gateway'): container('gwsubnet','GatewaySubnet','hub','subnet'); node('gateway','Connectivity Gateway','vpn','gwsubnet')
        if has('private dns'): node('dns','Private DNS','dns','hub')

    spoke_count=num(r'spoke(?:s|\s+vnets?|\s+networks?)',0)
    numbered=[int(x) for x in re.findall(r'spoke(?:\s+network|\s+vnet)?\s*(\d+)',t)]
    if numbered: spoke_count=max(spoke_count,max(numbered))
    if 'spoke' in t and not spoke_count: spoke_count=1
    apps_each=1
    m=re.search(r'(\d+)\s+applications?.{0,50}(?:each|per)',t)
    if m: apps_each=int(m.group(1))
    else:
        for w,n in {'one':1,'two':2,'three':3,'four':4,'five':5}.items():
            if re.search(r'\b'+w+r'\s+applications?.{0,50}(?:each|per)',t): apps_each=n
    for s in range(1,spoke_count+1):
        sid=f'spoke{s}'; container(sid,f'Spoke VNet {s}',root); sub=f'appsub{s}'; container(sub,'Application Subnet',sid,'subnet')
        for a in range(1,apps_each+1): node(f'app{s}_{a}',f'Application {a}','app',sub)
        if hub: edge('hub',sid,'VNet Peering')

    # Named/tier subnets for conventional application architectures.
    for key,label in [('frontend','Frontend Subnet'),('backend','Backend Subnet'),('data','Data Subnet'),('management','Management Subnet')]:
        if key+' subnet' in t: container(key+'subnet',label,'hub' if hub and key=='management' else root,'subnet')
    frontend='frontendsubnet' if any(c['id']=='frontendsubnet' for c in containers) else root
    backend='backendsubnet' if any(c['id']=='backendsubnet' for c in containers) else root
    data='datasubnet' if any(c['id']=='datasubnet' for c in containers) else root

    # Common Azure resources.
    if has('front door'): node('frontdoor','Azure Front Door','frontdoor',root)
    if has('application gateway','waf'): node('appgw','Application Gateway / WAF','appgw',frontend)
    if has('load balancer'): node('lb','Azure Load Balancer','lb',frontend)
    if has('api management','apim'): node('apim','API Management','apim',backend)
    if has('app service','web app'): node('webapp','App Service','app',backend)
    if has('function app','azure function'): node('function','Function App','function',backend)
    if has('aks','kubernetes'): node('aks','Azure Kubernetes Service','aks',backend)
    if has('virtual machine',' vm ','vms'): node('vm','Virtual Machines','vm',backend)
    if has('service bus'): node('servicebus','Service Bus','servicebus',root)
    if has('event grid'): node('eventgrid','Event Grid','eventgrid',root)
    if has('key vault'): node('keyvault','Azure Key Vault','keyvault',data)
    if has('sql'): node('sql','Azure SQL','sql',data)
    if has('cosmos'): node('cosmos','Cosmos DB','cosmos',data)
    if has('storage','blob'): node('storage','Azure Storage','storage',data)
    if has('redis'): node('redis','Azure Cache for Redis','redis',data)
    if has('log analytics'): node('logs','Log Analytics','monitor',root)
    if has('application insights'): node('insights','Application Insights','monitor',root)
    if has('monitor') and not has('application insights'): node('monitor','Azure Monitor','monitor',root)

    ids={n['id'] for n in nodes}
    # Build sensible flows only when both endpoints exist.
    chain=[x for x in ['frontdoor','appgw','lb','apim','webapp','aks'] if x in ids]
    for a,b in zip(chain,chain[1:]): edge(a,b,'HTTPS')
    if 'webapp' in ids and 'function' in ids and has('web app','app service'): edge('webapp','function','Invoke')
    for d in ['sql','cosmos','storage','redis']:
        if 'webapp' in ids and d in ids: edge('webapp',d,'Private access' if has('private endpoint','private link') else 'Data')
        elif 'aks' in ids and d in ids: edge('aks',d,'Private access' if has('private endpoint','private link') else 'Data')
    if 'webapp' in ids and 'keyvault' in ids: edge('webapp','keyvault','Secrets')
    if 'aks' in ids and 'keyvault' in ids: edge('aks','keyvault','Secrets')
    if 'function' in ids and 'servicebus' in ids: edge('servicebus','function','Trigger')
    if 'function' in ids and 'sql' in ids: edge('function','sql','Data')
    for source in ['webapp','function','aks']:
        for mon in ['logs','insights','monitor']:
            if source in ids and mon in ids: edge(source,mon,'Telemetry')
    if has('outbound','egress') and 'firewall' in ids:
        notes.append('Outbound traffic routed through Azure Firewall')
        for s in range(1,spoke_count+1): edge(f'spoke{s}','firewall','0.0.0.0/0 via firewall')
    if has('private endpoint','private link'): notes.append('Data services use private connectivity')
    if not nodes: node('workload','Workload','app',root)
    return {'provider':'Azure' if azure else 'Cloud','source_requirement':text,'containers':containers,'nodes':nodes,'edges':edges,'traffic_notes':notes,'layout':{'direction':'TB' if has('top','below','bottom','north south') else 'LR'}}

# Imports are pinned to names verified with diagrams==0.24.4.
def pycode(model):
    imports='''from diagrams import Diagram, Cluster, Edge\nfrom diagrams.azure.network import Firewall, VirtualNetworks, VirtualNetworkGateways, ApplicationGateway, FrontDoors, LoadBalancers\nfrom diagrams.azure.compute import AppServices, FunctionApps, KubernetesServices, VM\nfrom diagrams.azure.integration import ServiceBus, APIManagement\nfrom diagrams.azure.security import KeyVaults\nfrom diagrams.azure.database import SQLDatabases, CosmosDb, CacheForRedis\nfrom diagrams.azure.storage import StorageAccounts\nfrom diagrams.azure.devops import ApplicationInsights\nfrom diagrams.azure.general import Resource\n'''
    cls={'firewall':'Firewall','app':'AppServices','function':'FunctionApps','servicebus':'ServiceBus','frontdoor':'FrontDoors','appgw':'ApplicationGateway','lb':'LoadBalancers','apim':'APIManagement','keyvault':'KeyVaults','sql':'SQLDatabases','cosmos':'CosmosDb','redis':'CacheForRedis','storage':'StorageAccounts','monitor':'ApplicationInsights','bastion':'VirtualNetworks','vpn':'VirtualNetworkGateways','dns':'Resource','aks':'KubernetesServices','vm':'VM','eventgrid':'Resource'}
    children={}; nodechildren={}
    for c in model['containers']: children.setdefault(c.get('parent'),[]).append(c)
    for n in model['nodes']: nodechildren.setdefault(n.get('parent'),[]).append(n)
    direction=model.get('layout',{}).get('direction','LR')
    lines=[imports,f'with Diagram("Generated Architecture", filename="diagrams/generated_architecture", outformat="png", show=False, direction="{direction}", graph_attr={{"compound":"true","splines":"spline","nodesep":"0.8","ranksep":"1.0","pad":"0.4"}}):','    n = {}','    anchors = {}']
    def emit(parent,indent):
        for n in nodechildren.get(parent,[]): lines.append(' '*indent+f'n["{n["id"]}"] = {cls.get(n["type"],"Resource")}("{n["label"]}")')
        for c in children.get(parent,[]):
            lines.append(' '*indent+f'with Cluster("{c["label"]}"):'); lines.append(' '*(indent+4)+f'anchors["{c["id"]}"] = VirtualNetworks("")'); emit(c['id'],indent+4)
    emit(None,4)
    nodeids={n['id'] for n in model['nodes']}; containerids={c['id'] for c in model['containers']}
    def ref(x): return f'n["{x}"]' if x in nodeids else f'anchors["{x}"]'
    for a,b,label in model['edges']:
        if a in nodeids|containerids and b in nodeids|containerids: lines.append(f'    {ref(a)} >> Edge(label="{label}") >> {ref(b)}')
    return '\n'.join(lines)+'\n'

# Override app.py functions used by the live Flask routes.
app.view_functions['generate'].__globals__['interpret']=interpret
app.view_functions['generate'].__globals__['pycode']=pycode

CONTOSO='''Create an Azure architecture for Contoso with one VNet containing a frontend subnet, backend subnet and data subnet. Use Azure Front Door, Application Gateway WAF, App Service web app, Function App, Service Bus, Azure SQL Database, Storage Account, Key Vault with private endpoints, Log Analytics and Application Insights. Users access Front Door then Application Gateway then the web app. The web app accesses SQL, Storage and Key Vault. The Function App uses Service Bus. Show monitoring and place data services in the data subnet.'''
HUBSPOKE='''Create an Azure landing zone with Azure Firewall and Bastion in a Hub VNet and two Spoke VNets. Each spoke should contain two applications. Peer both spokes with the Hub VNet and route outbound traffic through the Azure Firewall.'''

def regression(requirement):
    ok,detail=graphviz_check()
    if not ok:return {'status':'failed','stage':'graphviz','error':detail},500
    try:
        model=interpret(requirement); code=pycode(model); p=os.path.join(BASE,'regression_generated.py'); open(p,'w').write(code)
        run=subprocess.run(['python',p],cwd=BASE,capture_output=True,text=True,timeout=30); png=os.path.join(OUT,'generated_architecture.png')
        if run.returncode!=0:return {'status':'failed','stage':'python','stderr':run.stderr[-3000:]},500
        drawio=os.path.join(OUT,'regression.drawio'); open(drawio,'w').write(drawio_xml(model))
        if not os.path.exists(png) or os.path.getsize(png)==0 or not os.path.exists(drawio):return {'status':'failed','stage':'artifacts'},500
        return {'status':'passed','graphviz':detail,'png_bytes':os.path.getsize(png),'drawio':True,'nodes':len(model['nodes']),'containers':len(model['containers']),'edges':len(model['edges'])},200
    except Exception as e:return {'status':'failed','stage':'exception','error':repr(e)},500

@app.get('/regression/contoso')
def regression_contoso(): return regression(CONTOSO)
@app.get('/regression/hubspoke')
def regression_hubspoke(): return regression(HUBSPOKE)
def regression_health():
    a,sa=regression(CONTOSO)
    if sa!=200:return a,sa
    b,sb=regression(HUBSPOKE)
    return {'status':'passed','contoso':a,'hubspoke':b},sb
app.view_functions['health']=regression_health
