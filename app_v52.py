# Safe launcher for V5.2. Keeps the main renderer source intact while applying a
# one-line syntax-safe replacement before execution.
from pathlib import Path
src=Path(__file__).with_name('app_v5.py').read_text(encoding='utf-8')
old='def path(A,d,dash=False):A.append(f\'<path d="{d}" stroke="#0078d4" stroke-width="3" fill="none" {"stroke-dasharray=\\"7 6\\"" if dash else "marker-end=\\"url(#end)\\""}/>\')'
new='def path(A,d,dash=False):\n attr=\'stroke-dasharray="7 6"\' if dash else \'marker-end="url(#end)"\'\n A.append(f\'<path d="{d}" stroke="#0078d4" stroke-width="3" fill="none" {attr}/>\')'
if old not in src:
    raise RuntimeError('Expected V5.2 path helper not found; refusing to launch an unverified source')
src=src.replace(old,new)
ns={'__name__':'app_v52','__file__':str(Path(__file__).with_name('app_v5.py'))}
exec(compile(src,'app_v5.py','exec'),ns)
app=ns['app']
