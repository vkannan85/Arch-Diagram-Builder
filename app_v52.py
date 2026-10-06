# Safe launcher for V5.2 plus deployment-blocking regression verification.
from pathlib import Path
from flask import jsonify
src=Path(__file__).with_name('app_v5.py').read_text(encoding='utf-8')
old='def path(A,d,dash=False):A.append(f\'<path d="{d}" stroke="#0078d4" stroke-width="3" fill="none" {"stroke-dasharray=\\"7 6\\"" if dash else "marker-end=\\"url(#end)\\""}/>\')'
new='def path(A,d,dash=False):\n attr=\'stroke-dasharray="7 6"\' if dash else \'marker-end="url(#end)"\'\n A.append(f\'<path d="{d}" stroke="#0078d4" stroke-width="3" fill="none" {attr}/>\')'
if old not in src:
    raise RuntimeError('Expected V5.2 path helper not found; refusing to launch an unverified source')
src=src.replace(old,new)
ns={'__name__':'app_v52','__file__':str(Path(__file__).with_name('app_v5.py'))}
exec(compile(src,'app_v5.py','exec'),ns)
app=ns['app']

@app.route('/selftest')
def selftest():
    ns['load_icons']()
    required=['frontdoor','appgw','loadbalancer','vm','sql','storage','keyvault','monitor','loganalytics','nsg','privateendpoint','firewall','gateway','expressroute']
    missing=[x for x in required if x not in ns['ICONS']]
    model=ns['parse_requirement'](ns['TEST_REQ'])
    picture=ns['svg'](model)
    labels={r['id'] for r in model.get('resources',[])}
    expected={'frontdoor','appgw','loadbalancer','sql','storage','keyvault','monitor','loganalytics','nsg'}
    subnets={(s['name'].lower(),s['cidr']) for s in model.get('subnets',[])}
    expected_subnets={('application gateway subnet','10.10.1.0/24'),('application subnet','10.10.2.0/24'),('database subnet','10.10.3.0/24')}
    checks={
      'icon_pack_error':not bool(ns['ICON_ERROR']),
      'all_official_icons':not missing,
      'no_missing_markers':'data-missing-icon=' not in picture,
      'embedded_icons':picture.count('data:image/svg+xml;base64,')>=10,
      'vnet':model.get('vnet',{}).get('name')=='Production-VNet' and model.get('vnet',{}).get('cidr')=='10.10.0.0/16',
      'subnets':expected_subnets.issubset(subnets),
      'vms':model.get('vms')[:2]==['WEB-VM01','WEB-VM02'],
      'resources':expected.issubset(labels),
      'private_endpoint_intent':bool(model.get('privateendpoint')),
      'paas_outside_vnet_note':'PaaS services remain outside the VNet' in picture,
      'mobile_viewbox':'viewBox="0 0 1800 1050"' in picture}
    ok=all(checks.values())
    return jsonify({'ok':ok,'checks':checks,'missing_icons':missing,'resolved_icons':ns['ICON_FILES'],'model_type':model.get('type'),'version':'v5.2'}),200 if ok else 503
