from flask import Flask, send_file, render_template_string
import os, subprocess
app=Flask(__name__)
BASE=os.path.dirname(__file__); OUT=os.path.join(BASE,"diagrams"); os.makedirs(OUT,exist_ok=True)
HTML='''<!doctype html><title>Arch Diagram Builder Demo</title><style>body{font-family:Arial;margin:40px;background:#f5f7fb;color:#17233c}button,a{padding:12px 16px;margin:6px;background:#1677ff;color:white;border:0;border-radius:8px;text-decoration:none;display:inline-block}img{max-width:100%;background:white;border:1px solid #ddd;margin-top:20px}</style><h1>Arch Diagram Builder Demo</h1><p>Python diagrams + GraphViz + editable Draw.io, based on the reference repository workflow.</p><form method=post action=/generate><button>Generate Contoso Architecture</button></form>{% if ready %}<a href=/png>View/download PNG</a><a href=/drawio>Download editable Draw.io</a><br><img src=/png>{% endif %}'''
@app.get("/")
def home(): return render_template_string(HTML,ready=os.path.exists(os.path.join(OUT,"contoso_architecture.png")))
@app.post("/generate")
def generate():
 subprocess.run(["python","contoso_architecture.py"],cwd=BASE,check=True)
 return render_template_string(HTML,ready=True)
@app.get("/png")
def png(): return send_file(os.path.join(OUT,"contoso_architecture.png"),mimetype="image/png")
@app.get("/drawio")
def drawio(): return send_file(os.path.join(OUT,"contoso_architecture.drawio"),as_attachment=True)
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","3000")))
