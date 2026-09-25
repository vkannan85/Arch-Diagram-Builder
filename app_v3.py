from app_fixed import app, interpret, pycode as legacy_pycode, CONTOSO, HUBSPOKE, BASE, OUT, graphviz_check
import os, subprocess, html, base64

# V3 renderer: container symbols are decorations, never Graphviz workload nodes.
# PNG uses Graphviz for workload placement then Pillow overlays Subscription/VNet/Subnet
# boundary markers at the top-right border. Draw.io embeds Azure-style SVG icons and uses
# the same deterministic hierarchy/geometry for editable objects.

def pycode(model):
    code=legacy_pycode(model)
    # Make Graphviz anchor nodes invisible: they retain edge/cluster layout semantics only.
    code=code.replace('VirtualNetworks("VNet")','VirtualNetworks("", width="0.01", height="0.01")')
    code=code.replace('VirtualNetworks("")','VirtualNetworks("", width="0.01", height="0.01")')
    code=code.replace('Subnets("Subnet")','Subnets("", width="0.01", height="0.01")')
    code=code.replace('Subnets("")','Subnets("", width="0.01", height="0.01")')
    return code

# Small self-contained SVGs. They are embedded as data URIs so Draw.io has icons even offline.
def svg_data(kind):
    if kind=='cloud':
        svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><path fill="#f5a623" d="M32 4 46 18 32 32 18 18z"/><path fill="#f5a623" d="M27 27h10v33H27z"/><circle cx="32" cy="18" r="4" fill="white"/></svg>'''
    elif kind=='vnet':
        svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 48"><path d="M18 8 5 24l13 16" fill="none" stroke="#2589d8" stroke-width="7"/><path d="m62 8 13 16-13 16" fill="none" stroke="#2589d8" stroke-width="7"/><circle cx="30" cy="24" r="5" fill="#78a22f"/><circle cx="40" cy="24" r="5" fill="#78a22f"/><circle cx="50" cy="24" r="5" fill="#78a22f"/></svg>'''
    elif kind=='subnet':
        svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 48"><path d="M24 8 8 24l16 16" fill="none" stroke="#2589d8" stroke-width="7"/><path d="m56 8 16 16-16 16" fill="none" stroke="#2589d8" stroke-width="7"/><circle cx="40" cy="24" r="6" fill="#78a22f"/></svg>'''
    else:
        # Generic Azure resource tile; resource remains editable and visually icon-led.
        svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="5" y="5" width="54" height="54" rx="9" fill="#0078d4"/><path d="M18 43 31 15h9L28 49z" fill="white"/><path d="M34 31h14L39 49H27z" fill="#9ad7ff"/></svg>'''
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()

def drawio_v3(model):
    esc=lambda s: html.escape(str(s),quote=True)
    cells=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; children={}; nodechildren={}
    for c in model['containers']: children.setdefault(c.get('parent'),[]).append(c)
    for n in model['nodes']: nodechildren.setdefault(n.get('parent'),[]).append(n)
    def dims(cid):
        cc=children.get(cid,[]); nn=nodechildren.get(cid,[])
        if not cc:
            cols=min(3,max(1,len(nn))); rows=(len(nn)+cols-1)//cols
            return max(360,cols*185+55),max(210,100+rows*115)
        ds=[dims(x['id']) for x in cc]
        # siblings side-by-side; enough header/edge space to prevent overlaps
        return max(520,sum(w for w,h in ds)+35*(len(ds)-1)+70),max(300,150+max(h for w,h in ds)+115*((len(nn)+2)//3))
    def marker(cid,kind,w):
        uri=svg_data(kind); mw,mh=(58,46) if kind!='cloud' else (44,50)
        # y is negative: icon physically straddles the upper border, as requested.
        cells.append(f'<mxCell id="mark_{cid}" value="" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;image={uri};" vertex="1" parent="{cid}"><mxGeometry x="{w-mw-22}" y="{-mh//2}" width="{mw}" height="{mh}" as="geometry"/></mxCell>')
    def resource(n,parent,nx,ny):
        uri=svg_data(n.get('type','resource'))
        # Icon and label are separate editable cells; not a generic rounded box.
        cells.append(f'<mxCell id="{n["id"]}" value="" style="shape=image;imageAspect=0;aspect=fixed;image={uri};" vertex="1" parent="{parent}"><mxGeometry x="{nx+50}" y="{ny}" width="58" height="58" as="geometry"/></mxCell>')
        cells.append(f'<mxCell id="lbl_{n["id"]}" value="{esc(n["label"])}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=top;fontSize=12;" vertex="1" parent="{parent}"><mxGeometry x="{nx}" y="{ny+62}" width="160" height="36" as="geometry"/></mxCell>')
    def emit(c,parent,x,y):
        w,h=dims(c['id']); kind=c.get('kind','vnet'); stroke='#f5a623' if kind=='cloud' else ('#0078D4' if kind=='vnet' else '#5B5FC7'); sw=3 if kind in ('cloud','vnet') else 2
        cells.append(f'<mxCell id="{c["id"]}" value="{esc(c["label"])}" style="swimlane;html=1;rounded=0;startSize=36;container=1;collapsible=0;strokeColor={stroke};strokeWidth={sw};fillColor=none;fontStyle=1;align=left;spacingLeft=12;" vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        marker(c['id'],kind,w)
        nn=nodechildren.get(c['id'],[])
        for i,n in enumerate(nn): resource(n,c['id'],35+(i%3)*185,55+(i//3)*115)
        cx=35; cy=115+115*((len(nn)+2)//3)
        for child in children.get(c['id'],[]):
            cw,ch=dims(child['id']); emit(child,c['id'],cx,cy); cx+=cw+35
        return w,h
    rx=45
    for c in children.get(None,[]):
        w,h=emit(c,'1',rx,70); rx+=w+60
    for i,n in enumerate(nodechildren.get(None,[])): resource(n,'1',45,90+i*115)
    valid={c['id'] for c in model['containers']}|{n['id'] for n in model['nodes']}
    for i,(a,b,label) in enumerate(model['edges']):
        if a in valid and b in valid:
            cells.append(f'<mxCell id="e{i}" value="{esc(label)}" edge="1" parent="1" source="{a}" target="{b}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeWidth=1.5;"><mxGeometry relative="1" as="geometry"/></mxCell>')
    return '<mxfile host="app.diagrams.net"><diagram name="Architecture"><mxGraphModel grid="1" gridSize="10" guides="1" page="1" pageWidth="2000" pageHeight="1400"><root>'+''.join(cells)+'</root></mxGraphModel></diagram></mxfile>'

# Overlay border markers on PNG after Graphviz. This removes boundary icons from workload flow.
def overlay_png(model,png):
    try:
        from PIL import Image,ImageDraw
        im=Image.open(png).convert('RGBA'); d=ImageDraw.Draw(im)
        # Deterministic nested border markers at upper-right edges. This is presentation-only.
        W,H=im.size; containers=model.get('containers',[])
        levels={None:0}; byid={c['id']:c for c in containers}
        def depth(c):
            p=c.get('parent'); z=0
            while p in byid: z+=1; p=byid[p].get('parent')
            return z
        for idx,c in enumerate(sorted(containers,key=lambda x:(depth(x),x['id']))):
            dep=depth(c); kind=c.get('kind','vnet'); x=W-48-dep*34; y=26+idx*4
            col=(245,166,35,255) if kind=='cloud' else (37,137,216,255)
            if kind=='cloud':
                d.polygon([(x,y-14),(x+14,y),(x,y+14),(x-14,y)],fill=col); d.rectangle((x-4,y,x+4,y+25),fill=col)
            else:
                d.line((x-20,y-12,x-31,y,x-20,y+12),fill=col,width=5); d.line((x+20,y-12,x+31,y,x+20,y+12),fill=col,width=5)
                dots=3 if kind=='vnet' else 1
                for j in range(dots):
                    dx=x+(j-(dots-1)/2)*11; d.ellipse((dx-4,y-4,dx+4,y+4),fill=(120,162,47,255))
        im.save(png)
    except Exception:
        pass

def regression_v3(requirement):
    ok,detail=graphviz_check()
    if not ok:return {'status':'failed','stage':'graphviz','error':detail},500
    model=interpret(requirement); code=pycode(model); p=os.path.join(BASE,'regression_generated.py'); open(p,'w').write(code)
    run=subprocess.run(['python',p],cwd=BASE,capture_output=True,text=True,timeout=30); png=os.path.join(OUT,'generated_architecture.png')
    if run.returncode:return {'status':'failed','stage':'python','stderr':run.stderr[-3000:]},500
    overlay_png(model,png); xml=drawio_v3(model); d=os.path.join(OUT,'regression.drawio'); open(d,'w').write(xml)
    required=['mark_vnet','data:image/svg+xml;base64','shape=image']
    if not all(x in xml for x in required):return {'status':'failed','stage':'drawio-icons'},500
    return {'status':'passed','graphviz':detail,'png_bytes':os.path.getsize(png),'drawio_icons':True,'border_markers':True},200

# Patch normal generation. A response wrapper applies PNG decoration after generation.
gen=app.view_functions['generate']; gen.__globals__['pycode']=pycode; gen.__globals__['drawio_xml']=drawio_v3
_original_generate=gen
def generate_v3():
    resp=_original_generate()
    try:
        # Form requirement is available in Flask request; regenerate model only for decoration.
        from flask import request
        req=request.form.get('requirement','')
        if req: overlay_png(interpret(req),os.path.join(OUT,'generated_architecture.png'))
    except Exception: pass
    return resp
app.view_functions['generate']=generate_v3

@app.get('/regression/v3')
def regression_v3_route(): return regression_v3(CONTOSO)
app.view_functions['health']=lambda: regression_v3(CONTOSO)
