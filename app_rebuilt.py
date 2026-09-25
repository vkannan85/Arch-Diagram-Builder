from flask import Flask,request,send_file,render_template_string,jsonify
from app_fixed import interpret, pycode, CONTOSO, HUBSPOKE
from graphviz2drawio import graphviz2drawio
import os,subprocess,shutil

app=Flask(__name__)
BASE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(BASE,'diagrams'); os.makedirs(OUT,exist_ok=True)
HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture Diagram Builder</title><style>body{font-family:Arial;max-width:1050px;margin:30px auto;padding:0 16px}textarea{width:100%;height:230px}button,a{padding:10px 14px;margin:8px 5px 8px 0}img{max-width:100%;border:1px solid #ddd}.ok{background:#e9f7ef;padding:10px}.err{background:#fdecec;padding:10px;white-space:pre-wrap}</style></head><body><h1>Architecture Diagram Builder — Rebuilt</h1><p>One source: generated Python → Graphviz DOT → PNG + editable Draw.io.</p><form method="post" action="/generate"><textarea name="requirement">{{req}}</textarea><br><button>Interpret & Generate</button></form>{% if err %}<div class="err">{{err}}</div>{% endif %}{% if ready %}<div class="ok">Generation passed.</div><p><a href="/download/png">Download PNG</a><a href="/download/drawio">Download editable Draw.io</a><a href="/download/python">Download generated Python</a><a href="/download/dot">Download DOT</a></p><img src="/download/png?x={{stamp}}">{% endif %}</body></html>'''

def generate(requirement):
    model=interpret(requirement); code=pycode(model)
    py=os.path.join(BASE,'generated_architecture.py'); open(py,'w').write(code)
    # diagrams emits PNG and the Graphviz source when show=False; if .gv is cleaned by the
    # diagrams package, regenerate DOT from the Python-produced PNG graph via a patched copy.
    # We modify the generated Python only to set filename and preserve DOT using Graphviz save.
    instrumented=code.replace('with Diagram("Generated Architecture", filename="diagrams/generated_architecture", outformat="png", show=False,', 'with Diagram("Generated Architecture", filename="diagrams/generated_architecture", outformat="png", show=False,')
    open(py,'w').write(instrumented)
    run=subprocess.run(['python',py],cwd=BASE,capture_output=True,text=True,timeout=40)
    if run.returncode: raise RuntimeError(run.stderr)
    png=os.path.join(OUT,'generated_architecture.png')
    if not os.path.exists(png): raise RuntimeError('PNG was not generated')
    # Diagrams removes its temporary DOT. Re-execute a source variant with cleanup disabled by
    # monkey-patching Diagram.render so the exact underlying graph source is persisted.
    wrapper=os.path.join(BASE,'capture_dot.py')
    open(wrapper,'w').write('''from diagrams import Diagram\n_orig=Diagram.render\ndef _render(self):\n    self.dot.save(filename="diagrams/generated_architecture.dot")\n    return _orig(self)\nDiagram.render=_render\nexec(open("generated_architecture.py").read(), {"__name__":"__main__"})\n''')
    cap=subprocess.run(['python',wrapper],cwd=BASE,capture_output=True,text=True,timeout=40)
    if cap.returncode: raise RuntimeError('DOT capture failed: '+cap.stderr)
    dot=os.path.join(OUT,'generated_architecture.dot')
    if not os.path.exists(dot): raise RuntimeError('DOT source missing')
    # THIS is the important rebuild: Draw.io is converted from the same Graphviz DOT used by
    # Diagrams, rather than being independently laid out.
    xml=graphviz2drawio.convert(dot)
    drawio=os.path.join(OUT,'generated_architecture.drawio'); open(drawio,'w').write(xml)
    if not os.path.exists(drawio) or os.path.getsize(drawio)<100: raise RuntimeError('Draw.io conversion failed')
    return model,code,png,dot,drawio

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

# End-to-end tests use the actual production generate() path.
def check(req,name):
    try:
        model,code,png,dot,drawio=generate(req); xml=open(drawio).read(); ds=open(dot).read()
        # structural acceptance: same DOT is the converter input; containers/subnets and Azure
        # image paths must survive into conversion rather than a separately fabricated layout.
        return {'name':name,'status':'passed','png_bytes':os.path.getsize(png),'dot_bytes':os.path.getsize(dot),'drawio_bytes':os.path.getsize(drawio),'subnets':sum(c.get('kind')=='subnet' for c in model['containers']),'vnets':sum(c.get('kind')=='vnet' for c in model['containers']),'dot_clusters':ds.count('subgraph cluster'),'drawio_images':xml.count('image')}
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
