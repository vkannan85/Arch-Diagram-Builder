from flask import Flask,request,send_file,render_template_string,jsonify
from app_fixed import interpret, pycode, CONTOSO, HUBSPOKE
import os,subprocess,html,re,base64

app=Flask(__name__)
BASE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(BASE,'diagrams'); os.makedirs(OUT,exist_ok=True)
HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Diagram Builder</title><style>body{font-family:Arial;max-width:1050px;margin:30px auto;padding:0 16px}textarea{width:100%;height:230px}button,a{padding:10px 14px;margin:8px 5px 8px 0}img{max-width:100%;border:1px solid #ddd}.ok{background:#e9f7ef;padding:10px}.err{background:#fdecec;padding:10px;white-space:pre-wrap}</style></head><body><h1>Architecture Diagram Builder</h1><p>One Graphviz layout drives PNG and editable Draw.io.</p><form method="post" action="/generate"><textarea name="requirement">{{req}}</textarea><br><button>Interpret & Generate</button></form>{% if err %}<div class="err">{{err}}</div>{% endif %}{% if ready %}<div class="ok">Generation passed geometry/icon/edge validation.</div><p><a href="/download/png">Download PNG</a><a href="/download/drawio">Download editable Draw.io</a><a href="/download/python">Download generated Python</a><a href="/download/dot">Download DOT</a></p><img src="/download/png?x={{stamp}}">{% endif %}</body></html>'''

def q(s): return html.escape(str(s),quote=True)

def icon_uri(kind):
    # Embedded SVG means icons survive in a standalone editable .drawio file.
    glyph={'firewall':'FW','app':'APP','function':'FN','servicebus':'SB','frontdoor':'FD','appgw':'WAF','lb':'LB','apim':'API','keyvault':'KV','sql':'SQL','cosmos':'DB','redis':'R','storage':'ST','monitor':'MON','aks':'AKS','vm':'VM','vpn':'GW','dns':'DNS','eventgrid':'EV'}.get(kind,'AZ')
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 72"><rect x="4" y="4" width="64" height="64" rx="10" fill="#0078d4"/><path d="M18 48 33 16h10L29 56z" fill="white"/><text x="48" y="58" text-anchor="middle" font-family="Arial" font-size="11" font-weight="700" fill="white">{glyph}</text></svg>'''
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()

def boundary_uri(kind):
    if kind=='subnet': body='<path d="M22 7 7 24l15 17M58 7l15 17-15 17" fill="none" stroke="#2589d8" stroke-width="7"/><circle cx="40" cy="24" r="6" fill="#78a22f"/>'
    elif kind=='vnet': body='<path d="M18 7 5 24l13 17M62 7l13 17-13 17" fill="none" stroke="#2589d8" stroke-width="7"/><circle cx="29" cy="24" r="5" fill="#78a22f"/><circle cx="40" cy="24" r="5" fill="#78a22f"/><circle cx="51" cy="24" r="5" fill="#78a22f"/>'
    else: body='<path d="M40 3 57 20 40 37 23 20zM35 35h10v31H35z" fill="#f5a623"/>'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 70">{body}</svg>'
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()

def graphviz_json(dot):
    p=subprocess.run(['dot','-Tjson',dot],cwd=BASE,capture_output=True,text=True,timeout=30)
    if p.returncode: raise RuntimeError('Graphviz positioned JSON failed: '+p.stderr)
    import json; return json.loads(p.stdout)

def export_drawio(model,layout,path):
    # Graphviz JSON coordinates are points with origin bottom-left; mxGraph is px/top-left.
    scale=1.333333; bb=[float(x) for x in layout.get('bb','0,0,1000,800').split(',')]; gh=bb[3]
    cells=['<mxCell id="0"/>','<mxCell id="1" parent="0"/>']; objects=layout.get('objects',[])
    by_name={str(o.get('name')):o for o in objects}; model_nodes=model['nodes']; containers=model['containers']
    # Graphviz clusters expose bounding boxes in objects with names cluster_*.
    clusters={str(o.get('name','')).replace('cluster_','',1):o for o in objects if str(o.get('name','')).startswith('cluster_')}
    def rect_from_bb(b):
        a=[float(x) for x in str(b).split(',')]; return a[0]*scale,(gh-a[3])*scale,(a[2]-a[0])*scale,(a[3]-a[1])*scale
    # Containers first, so all editable resources and arrows appear above them.
    for c in containers:
        co=clusters.get(c['id']);
        if not co or not co.get('bb'): continue
        x,y,w,h=rect_from_bb(co['bb']); kind=c.get('kind','vnet'); stroke='#f5a623' if kind=='cloud' else ('#0078D4' if kind=='vnet' else '#5B5FC7')
        cells.append(f'<mxCell id="box_{q(c["id"])}" value="{q(c["label"])}" style="rounded=0;whiteSpace=wrap;html=1;strokeColor={stroke};strokeWidth={3 if kind!="subnet" else 2};fillColor=none;verticalAlign=top;align=left;spacingTop=8;spacingLeft=10;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" as="geometry"/></mxCell>')
        # Boundary icon straddles the exact top-right Graphviz cluster border.
        iw,ih=54,44; uri=boundary_uri(kind)
        cells.append(f'<mxCell id="mark_{q(c["id"])}" value="" style="shape=image;imageAspect=0;aspect=fixed;image={uri};" vertex="1" parent="1"><mxGeometry x="{x+w-iw-14:.1f}" y="{y-ih/2:.1f}" width="{iw}" height="{ih}" as="geometry"/></mxCell>')
    # Workload nodes at Graphviz's exact positioned coordinates.
    node_ids={}; expected_images=0
    for n in model_nodes:
        o=by_name.get(n['id'])
        if not o or not o.get('pos'): continue
        px,py=[float(v) for v in o['pos'].split(',')]; ww=float(o.get('width',1.4))*72*scale; hh=float(o.get('height',1.4))*72*scale; x=px*scale-ww/2; y=(gh-py)*scale-hh/2
        nid='node_'+n['id']; node_ids[n['id']]=nid; uri=icon_uri(n.get('type'))
        cells.append(f'<mxCell id="{q(nid)}" value="{q(n["label"])}" style="shape=image;imageAspect=0;aspect=fixed;image={uri};verticalLabelPosition=bottom;verticalAlign=top;align=center;spacingTop=5;fontSize=12;" vertex="1" parent="1"><mxGeometry x="{x:.1f}" y="{y:.1f}" width="{ww:.1f}" height="{hh:.1f}" as="geometry"/></mxCell>'); expected_images+=1
    # Graphviz JSON edges include spline control points in pos. Preserve those as mxGeometry waypoints.
    edges=layout.get('edges',[]); model_edges=model.get('edges',[]); edge_count=0
    # _gvid lets us resolve Graphviz tail/head indices to object names.
    gvid={o.get('_gvid'):str(o.get('name')) for o in objects}
    for e in edges:
        a=gvid.get(e.get('tail')); b=gvid.get(e.get('head'))
        if a not in node_ids or b not in node_ids: continue
        label=''
        for ma,mb,ml in model_edges:
            if ma==a and mb==b: label=ml; break
        pos=e.get('pos',''); pts=[]
        for sx,sy in re.findall(r'(?<![es],)(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',pos):
            xx=float(sx)*scale; yy=(gh-float(sy))*scale; pts.append((xx,yy))
        # Remove endpoints; mxGraph attaches source/target itself, remaining points guide the spline route.
        mids=pts[1:-1] if len(pts)>2 else []
        geo='<mxGeometry relative="1" as="geometry">'
        if mids:
            geo+='<Array as="points">'+''.join(f'<mxPoint x="{x:.1f}" y="{y:.1f}"/>' for x,y in mids)+'</Array>'
        geo+='</mxGeometry>'
        cells.append(f'<mxCell id="edge_{edge_count}" value="{q(label)}" edge="1" parent="1" source="{q(node_ids[a])}" target="{q(node_ids[b])}" style="curved=1;rounded=1;html=1;endArrow=block;endFill=1;strokeWidth=1.5;">{geo}</mxCell>'); edge_count+=1
    xml='<mxfile host="app.diagrams.net"><diagram name="Architecture"><mxGraphModel grid="1" gridSize="10" guides="1" page="1" pageWidth="2200" pageHeight="1600"><root>'+''.join(cells)+'</root></mxGraphModel></diagram></mxfile>'
    open(path,'w').write(xml)
    return {'images':expected_images,'edges':edge_count,'markers':sum(1 for c in containers if c['id'] in clusters),'xml':xml}

def generate(requirement):
    model=interpret(requirement); code=pycode(model); py=os.path.join(BASE,'generated_architecture.py'); open(py,'w').write(code)
    run=subprocess.run(['python',py],cwd=BASE,capture_output=True,text=True,timeout=40)
    if run.returncode: raise RuntimeError(run.stderr)
    png=os.path.join(OUT,'generated_architecture.png')
    if not os.path.exists(png): raise RuntimeError('PNG was not generated')
    wrapper=os.path.join(BASE,'capture_dot.py')
    open(wrapper,'w').write('''from diagrams import Diagram\n_orig=Diagram.render\ndef _render(self):\n self.dot.save(filename="diagrams/generated_architecture.dot")\n return _orig(self)\nDiagram.render=_render\nexec(open("generated_architecture.py").read(), {"__name__":"__main__"})\n''')
    cap=subprocess.run(['python',wrapper],cwd=BASE,capture_output=True,text=True,timeout=40)
    if cap.returncode: raise RuntimeError('DOT capture failed: '+cap.stderr)
    dot=os.path.join(OUT,'generated_architecture.dot'); layout=graphviz_json(dot); drawio=os.path.join(OUT,'generated_architecture.drawio'); stats=export_drawio(model,layout,drawio)
    expected_nodes=len(model['nodes']); expected_edges=sum(1 for a,b,l in model['edges'] if a in {n['id'] for n in model['nodes']} and b in {n['id'] for n in model['nodes']})
    if stats['images'] < expected_nodes: raise RuntimeError(f'Draw.io icon validation failed: {stats["images"]}/{expected_nodes}')
    if stats['edges'] < expected_edges: raise RuntimeError(f'Draw.io edge validation failed: {stats["edges"]}/{expected_edges}')
    if stats['markers'] < len(model['containers']): raise RuntimeError(f'Draw.io boundary validation failed: {stats["markers"]}/{len(model["containers"])}')
    return model,code,png,dot,drawio,stats

@app.get('/')
def home(): return render_template_string(HTML,req=CONTOSO,ready=False,err=None)
@app.post('/generate')
def route_generate():
    req=request.form.get('requirement','').strip()
    try:
        generate(req); return render_template_string(HTML,req=req,ready=True,err=None,stamp=os.path.getmtime(os.path.join(OUT,'generated_architecture.png')))
    except Exception as e:return render_template_string(HTML,req=req,ready=False,err=str(e)),500
@app.get('/download/<kind>')
def download(kind):
    mp={'png':(os.path.join(OUT,'generated_architecture.png'),'architecture.png'),'drawio':(os.path.join(OUT,'generated_architecture.drawio'),'architecture.drawio'),'python':(os.path.join(BASE,'generated_architecture.py'),'architecture.py'),'dot':(os.path.join(OUT,'generated_architecture.dot'),'architecture.dot')}
    if kind not in mp:return 'not found',404
    return send_file(mp[kind][0],as_attachment=True,download_name=mp[kind][1])

def check(req,name):
    try:
        model,code,png,dot,drawio,s=generate(req)
        return {'name':name,'status':'passed','png_bytes':os.path.getsize(png),'drawio_bytes':os.path.getsize(drawio),'nodes':len(model['nodes']),'drawio_images':s['images'],'model_edges':len(model['edges']),'drawio_edges':s['edges'],'containers':len(model['containers']),'drawio_boundary_markers':s['markers'],'graphviz_geometry':True,'graphviz_edge_waypoints':True}
    except Exception as e:return {'name':name,'status':'failed','error':repr(e)}
@app.get('/regression/contoso')
def reg_contoso():
    r=check(CONTOSO,'contoso'); return jsonify(r),200 if r['status']=='passed' else 500
@app.get('/regression/hubspoke')
def reg_hub():
    r=check(HUBSPOKE,'hubspoke'); return jsonify(r),200 if r['status']=='passed' else 500
@app.get('/health')
def health():
    a=check(CONTOSO,'contoso'); b=check(HUBSPOKE,'hubspoke'); ok=a['status']==b['status']=='passed'; return jsonify({'status':'passed' if ok else 'failed','contoso':a,'hubspoke':b}),200 if ok else 500
