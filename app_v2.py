from app_fixed import app, interpret, pycode as base_pycode, regression, CONTOSO, HUBSPOKE
import html

# V2 presentation layer.
# Boundary markers are decorations, not workload nodes. This keeps Subscription/VNet/Subnet
# symbols out of the middle of their containers and places them on the top-right border.

def pycode(model):
    # Keep the proven Diagrams/Graphviz renderer for resource icons and regression safety.
    # Remove visible VNet/Subnet anchor labels so they no longer look like workload nodes.
    code = base_pycode(model)
    code = code.replace('VirtualNetworks("VNet")', 'VirtualNetworks("")')
    code = code.replace('Subnets("Subnet")', 'Subnets("")')
    return code


def drawio_v2(model):
    esc=lambda s: html.escape(str(s), quote=True)
    cells=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']
    children={}; nodechildren={}
    for c in model['containers']: children.setdefault(c.get('parent'), []).append(c)
    for n in model['nodes']: nodechildren.setdefault(n.get('parent'), []).append(n)

    # Geometry is deterministic and shared by every editable object. Sibling subnets are
    # separate boxes, laid out side-by-side when practical instead of nested/overlapping.
    def dims(cid):
        cc=children.get(cid,[]); nn=nodechildren.get(cid,[])
        if not cc:
            cols=min(3,max(1,len(nn)))
            rows=(len(nn)+cols-1)//cols
            return max(330,cols*190+50), max(190,90+rows*105)
        ds=[dims(x['id']) for x in cc]
        width=max(480,sum(w for w,h in ds)+30*(len(ds)-1)+60)
        height=max(260,120+max(h for w,h in ds)+105*((len(nn)+2)//3))
        return width,height

    # Azure-like boundary symbol. It deliberately overlaps the top border (y=-18), matching
    # the supplied reference: icon centred on the upper-right boundary, not inside the box.
    def boundary_marker(cid, kind, w):
        if kind=='cloud':
            label='SUB'; stroke='#D83B01'; glyph='◆'
        elif kind=='vnet':
            label='VNET'; stroke='#0078D4'; glyph='↔'
        else:
            label='SUBNET'; stroke='#0078D4'; glyph='↔'
        x=w-72
        cells.append(f'<mxCell id="mark_{cid}" value="{glyph}" style="ellipse;html=1;whiteSpace=wrap;aspect=fixed;fillColor=#ffffff;strokeColor={stroke};strokeWidth=2;fontColor={stroke};fontSize=22;fontStyle=1;" vertex="1" parent="{cid}"><mxGeometry x="{x}" y="-18" width="38" height="38" as="geometry"/></mxCell>')
        cells.append(f'<mxCell id="marklbl_{cid}" value="{label}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=8;fontStyle=1;fontColor={stroke};" vertex="1" parent="{cid}"><mxGeometry x="{x-10}" y="20" width="58" height="16" as="geometry"/></mxCell>')

    def emit_container(c, parentcell, x, y):
        w,h=dims(c['id']); kind=c.get('kind','vnet')
        stroke='#D83B01' if kind=='cloud' else ('#0078D4' if kind=='vnet' else '#5B5FC7')
        sw='3' if kind in ('cloud','vnet') else '2'
        cells.append(f'<mxCell id="{c["id"]}" value="{esc(c["label"])}" style="swimlane;html=1;rounded=0;startSize=34;horizontal=1;container=1;collapsible=0;strokeColor={stroke};strokeWidth={sw};fillColor=none;fontStyle=1;align=left;spacingLeft=12;" vertex="1" parent="{parentcell}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        boundary_marker(c['id'],kind,w)

        # Place direct workload nodes first, in a compact grid below the header.
        nn=nodechildren.get(c['id'],[])
        for i,n in enumerate(nn):
            nx=35+(i%3)*190; ny=55+(i//3)*105
            cells.append(f'<mxCell id="{n["id"]}" value="{esc(n["label"])}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#0078D4;strokeWidth=1.5;" vertex="1" parent="{c["id"]}"><mxGeometry x="{nx}" y="{ny}" width="160" height="62" as="geometry"/></mxCell>')

        # Child containers are true siblings. This is the key fix for multiple subnets.
        cx=30; cy=95+105*((len(nn)+2)//3)
        for child in children.get(c['id'],[]):
            cw,ch=dims(child['id']); emit_container(child,c['id'],cx,cy); cx+=cw+30
        return w,h

    # Root containers are laid out left-to-right on the page.
    rx=40
    for c in children.get(None,[]):
        w,h=emit_container(c,'1',rx,50); rx+=w+50

    # Nodes with no container (rare) remain editable and outside boundaries.
    for i,n in enumerate(nodechildren.get(None,[])):
        cells.append(f'<mxCell id="{n["id"]}" value="{esc(n["label"])}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#0078D4;" vertex="1" parent="1"><mxGeometry x="40" y="{80+i*90}" width="170" height="60" as="geometry"/></mxCell>')

    # Connect actual resources/containers only. Marker cells never participate in traffic flow.
    valid={c['id'] for c in model['containers']}|{n['id'] for n in model['nodes']}
    for i,(a,b,label) in enumerate(model['edges']):
        if a in valid and b in valid:
            cells.append(f'<mxCell id="e{i}" value="{esc(label)}" edge="1" parent="1" source="{a}" target="{b}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeWidth=1.5;"><mxGeometry relative="1" as="geometry"/></mxCell>')
    return '<mxfile host="app.diagrams.net"><diagram name="Architecture"><mxGraphModel grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1200"><root>'+''.join(cells)+'</root></mxGraphModel></diagram></mxfile>'

# Patch the live Flask route globals so both normal generation and downloads use V2.
app.view_functions['generate'].__globals__['pycode']=pycode
app.view_functions['generate'].__globals__['drawio_xml']=drawio_v2

# Patch regression globals as well, so health checks exercise this exporter.
if 'regression_contoso' in app.view_functions:
    app.view_functions['regression_contoso'].__globals__['drawio_bordered']=drawio_v2
if 'regression_hubspoke' in app.view_functions:
    app.view_functions['regression_hubspoke'].__globals__['drawio_bordered']=drawio_v2
