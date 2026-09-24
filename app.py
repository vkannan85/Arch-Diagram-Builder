from flask import Flask, send_file, render_template_string, request
import os, subprocess
app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,"diagrams"); os.makedirs(OUT,exist_ok=True)
HTML='''<!doctype html><title>Arch Diagram Builder</title><style>body{font-family:Arial;margin:32px;background:#f5f7fb;color:#17233c;max-width:1100px}.card{background:white;padding:22px;border-radius:14px;margin-bottom:18px}textarea{width:100%;min-height:280px;padding:14px;box-sizing:border-box}button,a,select{padding:12px 16px;margin:8px 6px 8px 0;border-radius:8px}button,a{background:#1677ff;color:white;border:0;text-decoration:none;display:inline-block}img{max-width:100%;border:1px solid #ddd;margin-top:20px}</style><h1>Arch Diagram Builder</h1><div class=card><form method=post action=/generate><h3>1. Technical requirements</h3><textarea name=requirements placeholder="Paste your architecture requirements here...">{{req}}</textarea><h3>2. Choose output</h3><select name=format><option value=drawio>Draw.io (editable)</option><option value=visio>Visio (.vsdx)</option></select><br><button>Generate Architecture</button></form></div>{% if ready %}<div class=card><h3>Generated architecture</h3><a href=/png>PNG preview</a><a href=/drawio>Download editable Draw.io</a>{% if visio %}<p><b>Visio:</b> This reference Python/GraphViz project does not natively generate VSDX yet. The editable Draw.io intermediate is provided while native VSDX is added.</p>{% endif %}<br><img src=/png></div>{% endif %}'''
@app.route("/")
def home(): return render_template_string(HTML,req="",ready=False,visio=False)
@app.post("/generate")
def generate():
 req=request.form.get("requirements","").strip(); fmt=request.form.get("format","drawio")
 open(os.path.join(BASE,"last_requirement.txt"),"w").write(req)
 subprocess.run(["python","contoso_architecture.py"],cwd=BASE,check=True)
 return render_template_string(HTML,req=req,ready=True,visio=fmt=="visio")
@app.get("/png")
def png(): return send_file(os.path.join(OUT,"contoso_architecture.png"),mimetype="image/png")
@app.get("/drawio")
def drawio(): return send_file(os.path.join(OUT,"contoso_architecture.drawio"),as_attachment=True,download_name="architecture.drawio")
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","3000")))
