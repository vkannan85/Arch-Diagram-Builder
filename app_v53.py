import re
from flask import Response, jsonify
import app_v52 as base

app=base.app
ns=base.ns
CIDR=ns['CIDR']
parse_requirement=ns['parse_requirement']
load_icons=ns['load_icons']
generic_svg=ns['generic_svg']
ICONS=ns['ICONS']
TEST_REQ=ns['TEST_REQ']
defs=ns['defs']; tx=ns['tx']; box=ns['box']; icon=ns['icon']; path=ns['path']
base_svg=ns['svg']

HUB_TEST_REQ='''Objective: Create an Azure Hub-and-Spoke network architecture diagram showing secure connectivity between Azure workloads and an On-Premises Datacentre.
Hub Virtual Network: Create an Azure Virtual Network named Hub-VNet. CIDR: 10.0.0.0/16. Deploy an Azure Firewall inside Hub-VNet. Deploy an ExpressRoute Gateway in Hub-VNet. Connect the ExpressRoute Gateway to an ExpressRoute Circuit. The ExpressRoute Circuit should provide private connectivity between Azure and the On-Premises Datacentre.
Spoke Virtual Network 01: Create a Virtual Network named Spoke1-VNet. CIDR: 10.1.0.0/16. Create a workload subnet: CIDR: 10.1.1.0/24. Deploy a Windows Server VM named VM01 inside this subnet.
Spoke Virtual Network 02: Create a Virtual Network named Spoke2-VNet. CIDR: 10.2.0.0/16. Create a workload subnet: CIDR: 10.2.1.0/24. Deploy a Windows Server VM named VM02 inside this subnet.
Connectivity: Create VNet Peering between Hub-VNet and Spoke1-VNet and Hub-VNet and Spoke2-VNet. Hub-to-Spoke: Allow forwarded traffic, Allow gateway transit. Spoke-to-Hub: Allow forwarded traffic, Use remote gateway.
Traffic Flow: On-Premises Datacentre -> ExpressRoute Circuit -> ExpressRoute Gateway -> Hub-VNet -> Spoke Virtual Networks.
Security: Spoke traffic should be capable of being routed through Azure Firewall for centralised inspection.
Diagram Requirements: Show GatewaySubnet inside Hub-VNet. Show AzureFirewallSubnet inside Hub-VNet. Show each workload subnet inside its respective Spoke VNet. Show ExpressRoute connectivity to the On-Premises Datacentre. Clearly label VNet peering connections. Do not invent CIDR ranges or IP addresses that have not been specified.'''

def _workload_cidrs(t):
    return re.findall(r'workload subnet[\s\S]{0,80}?CIDR\s*:\s*('+CIDR+r')',t,re.I)[:2]

def onprem_symbol(x,y):
    # On-premises is not an Azure service, so use a neutral datacentre glyph rather than an Azure-icon placeholder.
    return f'<g transform="translate({x},{y})"><rect x="0" y="15" width="82" height="58" rx="5" fill="#eef2f5" stroke="#607d8b" stroke-width="3"/><rect x="10" y="0" width="62" height="18" rx="3" fill="#607d8b"/><path d="M15 31H67M15 45H67M15 59H67" stroke="#607d8b" stroke-width="3"/><circle cx="23" cy="31" r="3" fill="#fff"/><circle cx="23" cy="45" r="3" fill="#fff"/><circle cx="23" cy="59" r="3" fill="#fff"/></g>'

def hub_svg_v53(m):
    t=m.get('source',''); wc=_workload_cidrs(t); W,H=1900,1050
    A=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs()}<rect width="100%" height="100%" fill="white"/>',tx(45,55,'Azure Hub-and-Spoke Hybrid Network Architecture',34,700),tx(45,86,'ExpressRoute private connectivity • centralised inspection • gateway transit',16,400,c='#5d7185')]
    A.extend([box(40,185,260,190,'#69797e','#f7f7f7',16,2),tx(170,220,'On-Premises Datacentre',19,700,'middle'),onprem_symbol(129,245),box(345,205,235,150,'#75b9e7','#fff',14,2),icon('expressroute',425,220,70,70),tx(462,325,'ExpressRoute Circuit',15,700,'middle')]); path(A,'M300 280H345')
    hx,hy,hw,hh=650,120,560,790
    A.extend([box(hx,hy,hw,hh,'#0078d4','#f3f9fe',20,3),tx(hx+25,hy+40,'Hub Virtual Network',23,700),tx(hx+25,hy+68,m['hub']['name']+' • '+(m['hub']['cidr'] or 'CIDR not specified'),14,400,c='#526a80'),box(700,230,460,225,'#8ab4d6','#fff',12),tx(720,262,'GatewaySubnet',17,700),tx(720,286,'CIDR: Not specified',13,400,c='#718295'),icon('gateway',875,305,82,82),tx(916,420,'ExpressRoute Gateway',15,700,'middle'),box(700,535,460,225,'#8ab4d6','#fff',12),tx(720,567,'AzureFirewallSubnet',17,700),tx(720,591,'CIDR: Not specified',13,400,c='#718295'),icon('firewall',875,610,82,82),tx(916,725,'Azure Firewall',15,700,'middle')]); path(A,'M580 280H620V345H700')
    for i,s in enumerate(m['spokes'][:2]):
        x=1320; y=120+i*445; cidr=wc[i] if i<len(wc) else 'Not specified'
        A.extend([box(x,y,520,350,'#39a869','#f5fff8',18,3),tx(x+24,y+38,'Spoke Virtual Network',21,700),tx(x+24,y+66,s['name']+' • '+(s['cidr'] or 'CIDR not specified'),14,400,c='#526a80'),box(x+45,y+105,430,190,'#8ab4d6','#fff',12),tx(x+65,y+138,'Workload subnet',16,700),tx(x+65,y+162,'CIDR: '+cidr,13,400,c='#718295'),icon('vm',x+220,y+180,76,76),tx(x+258,y+280,s['vm']+' • Windows Server',14,700,'middle')])
        py=y+185; A.append(f'<path d="M1210 {py}H1320" stroke="#0078d4" stroke-width="4" fill="none"/>'); A.append(f'<path d="M1224 {py-8}l-14 8 14 8M1306 {py-8}l14 8-14 8" stroke="#0078d4" stroke-width="3" fill="none"/>')
        A.extend([tx(1265,py-45,'VNet Peering',14,700,'middle'),tx(1265,py-24,'Hub→Spoke: forwarded traffic + gateway transit',10,400,'middle','#526a80'),tx(1265,py+31,'Spoke→Hub: forwarded traffic + remote gateway',10,400,'middle','#526a80')])
    A.extend([tx(45,955,'Traffic flow: On-Premises Datacentre → ExpressRoute Circuit → ExpressRoute Gateway → Hub-VNet → Spoke VNets',15,700),tx(45,982,'Security: Spoke traffic can be steered through Azure Firewall for centralised inspection. Route tables/UDRs are required to enforce this; route prefixes were not specified and are not invented.',13,400,c='#526a80'),tx(45,1010,'GatewaySubnet and AzureFirewallSubnet CIDRs: Not specified.',13,400,c='#526a80')]); return ''.join(A)+'</svg>'

def render_svg(m): return hub_svg_v53(m) if m and m.get('type')=='hubspoke' else base_svg(m)
def rsvg_v53():
    current=ns.get('CURRENT'); return Response(render_svg(current),mimetype='image/svg+xml') if current else Response('No diagram',404)
app.view_functions['rsvg']=rsvg_v53

def hub_checks():
    load_icons(); m=parse_requirement(HUB_TEST_REQ); s=hub_svg_v53(m)
    required=['Hub-VNet','10.0.0.0/16','Spoke1-VNet','10.1.0.0/16','10.1.1.0/24','VM01','Spoke2-VNet','10.2.0.0/16','10.2.1.0/24','VM02','GatewaySubnet','AzureFirewallSubnet','ExpressRoute Circuit','ExpressRoute Gateway','Azure Firewall','On-Premises Datacentre','VNet Peering','gateway transit','remote gateway','Route tables/UDRs']
    missing=[x for x in required if x not in s]; icon_missing=[k for k in ['gateway','firewall','expressroute','vm'] if k not in ICONS]; invented=any(x in s for x in ['10.0.1.0/24','10.0.2.0/24']); return m,s,missing,icon_missing,invented

@app.route('/selftest/hubspoke')
def selftest_hubspoke():
    m,s,missing,icon_missing,invented=hub_checks(); ok=m.get('type')=='hubspoke' and not missing and not icon_missing and not invented and 'data-missing-icon' not in s
    return jsonify({'ok':ok,'renderer':'v5.3.2-semantic-hubspoke','model_type':m.get('type'),'missing':missing,'missing_icons':icon_missing,'invented_hub_cidr':invented,'workload_cidrs':_workload_cidrs(HUB_TEST_REQ)}),200 if ok else 503

@app.route('/release-health')
def release_health():
    m,hs,hm,hi,inv=hub_checks(); web=parse_requirement(TEST_REQ); ws=generic_svg(web)
    wr=['WEB-VM01','WEB-VM02','Application Gateway / WAF','Azure Load Balancer','Azure SQL Database','Private Endpoint']; wm=[x for x in wr if x not in ws]; wi=[k for k in ['frontdoor','appgw','loadbalancer','vm','sql','storage','keyvault','privateendpoint','gateway','firewall','expressroute'] if k not in ICONS]
    ok=m.get('type')=='hubspoke' and not hm and not hi and not inv and not wm and not wi and 'data-missing-icon' not in ws+hs
    return jsonify({'ok':ok,'version':'v5.3.2','hub_missing':hm,'web_missing':wm,'missing_icons':wi,'hub_model_type':m.get('type')}),200 if ok else 503
