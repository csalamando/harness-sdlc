#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_styleguide.py — Genera styleguide.html (artefacto derivado, no editar a mano).

Renderiza el catálogo de componentes del sistema de diseño usando los tokens
canónicos emitidos por design_tokens.py. Sirve de wireframe de referencia de
las PANT-xx hasta que el prototipo Penpot se materialice, y como contrato
visual verificable en navegador.

Uso:  python docs/design-system/ux/build_styleguide.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[3]
                       / "skills" / "sdlc-orchestrator" / "scripts"))

import design_tokens  # noqa: E402

OUT = _HERE / "styleguide.html"


def swatch(tema: str, nombre: str, tok: dict) -> str:
    v = tok["value"]
    fg = design_tokens.doc()["color"][tema]["fg"]["value"]
    r = design_tokens.contrast(v, fg) if v.startswith("#") else None
    ratio = f"{r:.1f}:1" if r else "—"
    cls = "swatch" if v.startswith("#") else "swatch rgba"
    return (f'<div class="{cls}" style="background:{v}">'
            f'<span class="sw-name">--{nombre}</span>'
            f'<span class="sw-val">{v}</span>'
            f'<span class="sw-ratio">fg {ratio}</span></div>')


def build() -> str:
    d = design_tokens.doc()
    tokens_css = design_tokens.tokens_css("all")

    osc = d["color"]["oscuro"]
    claro = d["color"]["claro"]
    osc_sw = "\n".join(swatch("oscuro", k, v) for k, v in osc.items())
    claro_sw = "\n".join(swatch("claro", k, v) for k, v in claro.items())

    sizes = d["font"]["size"]
    type_rows = "\n".join(
        f'<div class="type-row"><span class="type-token">font.size.{k}</span>'
        f'<span class="type-sample" style="font-size:{v["value"]}">'
        f'Portal del proyecto — {v["px"]}px</span></div>'
        for k, v in sizes.items())

    page = f"""<!DOCTYPE html>
<html lang="es" data-theme="oscuro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Styleguide — Sistema de Diseño del arnés SDLC v{design_tokens.version()}</title>
<!-- artefacto derivado de docs/design-system/tokens.json — no editar a mano -->
<style>
{tokens_css}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
font-family:system-ui,'Segoe UI',sans-serif;padding:2rem 2.5rem 4rem;line-height:1.55}}
h1{{font-size:1.35rem;color:var(--txt);margin:.2rem 0 .3rem}}
h2{{font-size:1.08rem;color:var(--txt);margin:2rem 0 .6rem;border-bottom:1px solid var(--panel-bd);
padding-bottom:.35rem}}
.sub{{color:var(--sub);font-size:.85rem;margin-bottom:1.5rem}}
.wrap{{max-width:960px;margin:0 auto}}
.panel{{background:var(--panel-bg);border:1px solid var(--panel-bd);border-radius:12px;
padding:1.2rem;margin:1rem 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.6rem}}
.swatch{{border-radius:8px;padding:.5rem .6rem;min-height:64px;display:flex;flex-direction:column;
justify-content:flex-end;font-size:.7rem;border:1px solid var(--panel-bd)}}
.swatch span{{color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.5)}}
.swatch .sw-name{{font-weight:650}}
.swatch .sw-val,.swatch .sw-ratio{{opacity:.85}}
.type-row{{display:flex;align-items:baseline;gap:1rem;padding:.45rem 0;border-bottom:1px solid var(--panel-bd)}}
.type-token{{font-family:ui-monospace,Consolas,monospace;font-size:.73rem;color:var(--muted-aa);min-width:9rem}}
/* ── componentes (contrato del design-system.md §5) ── */
.btn{{background:var(--card-bg);border:1px solid var(--panel-bd);color:var(--fg);border-radius:8px;
padding:.32rem .7rem;font-size:.87rem;font-weight:600;cursor:pointer;font-family:inherit}}
.btn:hover{{border-color:var(--accent)}}
.btn:focus-visible{{outline:2px solid var(--focus);outline-offset:2px}}
.btn:disabled{{opacity:.5;cursor:not-allowed}}
.btn-primary{{background:var(--accent-strong);color:var(--on-accent);border-color:transparent}}
.btn-primary:hover{{filter:brightness(1.1)}}
.input{{background:var(--card-bg);border:1px solid var(--panel-bd);color:var(--fg);border-radius:8px;
padding:.4rem .8rem;font-size:.87rem;font-family:inherit;min-width:280px}}
.input:focus{{outline:none;border-color:var(--accent)}}
.input:focus-visible{{outline:2px solid var(--focus);outline-offset:2px}}
.input::placeholder{{color:var(--muted-aa)}}
.nav-item{{display:block;padding:.45rem .7rem;border-radius:8px;font-size:.87rem;color:var(--sub);
text-decoration:none;cursor:pointer}}
.nav-item:hover{{background:var(--card-bg);color:var(--fg)}}
.nav-item:focus-visible{{outline:2px solid var(--focus);outline-offset:2px}}
.nav-item.active{{box-shadow:inset 2px 0 0 var(--accent);color:var(--txt);background:var(--card-bg)}}
.chip{{display:inline-block;background:var(--card-bg);border:1px solid var(--panel-bd);border-radius:4px;
padding:1px 8px;font-size:.67rem;margin-right:.4rem}}
.chip.ok{{color:var(--ok);border-color:var(--ok)}}
.chip.warn{{color:var(--warn-text);border-color:var(--warn)}}
.chip.bad{{color:var(--bad);border-color:var(--bad)}}
.chip.info{{color:var(--accent);border-color:var(--accent)}}
.card{{background:var(--card-bg);border:1px solid var(--panel-bd);border-radius:12px;padding:1rem}}
table.demo{{border-collapse:collapse;width:100%;font-size:.88em}}
table.demo th,table.demo td{{border-bottom:1px solid var(--panel-bd);padding:.45em .7em;text-align:left}}
table.demo th{{color:var(--sub);font-size:.78em;text-transform:uppercase;letter-spacing:.04em}}
table.demo tr:hover td{{background:var(--card-bg)}}
.crumbs-demo{{display:flex;align-items:center;gap:.45rem;background:var(--panel-bg);
border:1px solid var(--panel-bd);border-radius:6px;padding:.3rem .7rem;font-size:.77rem;color:var(--muted-aa)}}
.crumbs-demo b{{color:var(--txt)}}
.qr-demo{{padding:.5rem .8rem;border-bottom:1px solid var(--panel-bd);cursor:pointer;border-radius:6px}}
.qr-demo:hover{{background:var(--card-bg)}}
.qc{{font-size:.67rem;color:var(--accent);text-transform:uppercase;letter-spacing:.05em}}
pre.demo{{background:var(--panel-bg);border:1px solid var(--panel-bd);border-radius:10px;padding:1rem;
overflow-x:auto;font-family:ui-monospace,'Cascadia Code',Consolas,monospace;font-size:.85em}}
kbd{{background:var(--card-bg);border:1px solid var(--panel-bd);border-radius:4px;padding:1px 6px;
font-family:ui-monospace,Consolas,monospace;font-size:.78em}}
.row{{display:flex;gap:.7rem;align-items:center;flex-wrap:wrap;margin:.6rem 0}}
.state{{border-radius:12px;border:1px solid var(--panel-bd);padding:1rem;min-height:90px}}
.state.loading{{display:flex;align-items:center;gap:.7rem;color:var(--sub)}}
.spinner{{width:18px;height:18px;border-radius:50%;border:2px solid var(--panel-bd);
border-top-color:var(--accent);animation:spin 1s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.state.empty{{color:var(--sub);font-style:italic}}
.state.error{{background:color-mix(in srgb, var(--bad) 12%, transparent);border-color:var(--bad)}}
.state.error b{{color:var(--bad)}}
.state.success{{border-color:var(--ok)}}
.state.success b{{color:var(--ok)}}
@media (prefers-reduced-motion: reduce){{.spinner{{animation:none}}}}
#themebtn{{position:fixed;top:1rem;right:1.5rem}}
.tag{{font-size:.67rem;color:var(--muted-aa);text-transform:uppercase;letter-spacing:.06em}}
</style>
</head>
<body>
<button id="themebtn" class="btn" aria-label="Cambiar tema">🌞 Tema</button>
<div class="wrap">
<h1>◈ Sistema de Diseño — arnés SDLC</h1>
<div class="sub">v{design_tokens.version()} · tokens canónicos: <code>docs/design-system/tokens.json</code> ·
fuentes: system-ui (sans) / ui-monospace (mono) · temas oscuro/claro</div>

<h2>1. Paleta — tema oscuro</h2>
<div class="grid">{osc_sw}</div>
<h2>2. Paleta — tema claro</h2>
<div class="grid">{claro_sw}</div>

<h2>3. Escala tipográfica</h2>
<div class="panel">{type_rows}</div>

<h2>4. Botones</h2>
<div class="panel">
  <div class="row">
    <button class="btn">Default</button>
    <button class="btn btn-primary">Primary</button>
    <button class="btn" disabled>Disabled</button>
    <button class="btn" aria-label="Colapsar menú">☰ Icon</button>
  </div>
  <div class="tag">estados: default · hover (borde --accent) · focus-visible (anillo --focus) · disabled (.5 opacidad)</div>
</div>

<h2>5. Input de búsqueda</h2>
<div class="panel">
  <div class="row"><input class="input" placeholder="Buscar… (Ctrl+K o /)" aria-label="Buscar"></div>
  <div class="tag">focus: borde --accent + anillo --focus · placeholder --muted-aa</div>
</div>

<h2>6. Navegación lateral</h2>
<div class="panel" style="max-width:320px">
  <a class="nav-item" tabindex="0">Inicio</a>
  <a class="nav-item active" aria-current="page" tabindex="0">Arquitectura</a>
  <a class="nav-item" tabindex="0">Documentación</a>
  <div class="tag" style="margin-top:.5rem">activo: barra --accent + aria-current · hover: fondo --card-bg</div>
</div>

<h2>7. Chips de estado</h2>
<div class="panel">
  <span class="chip ok">OK · 291 checks</span>
  <span class="chip warn">WARN · drift</span>
  <span class="chip bad">ERROR · gate</span>
  <span class="chip info">ADR-013</span>
</div>

<h2>8. Tarjeta y tabla</h2>
<div class="panel">
  <div class="card" style="margin-bottom:1rem"><b>Tarjeta</b><br>
  <span style="color:var(--sub);font-size:.85rem">Fondo --card-bg, radio 2xl, borde --panel-bd.</span></div>
  <table class="demo"><tr><th>Artefacto</th><th>Estado</th><th>Recibo</th></tr>
  <tr><td>design-system.md</td><td>✅ vigente</td><td>rc-2026-0912</td></tr>
  <tr><td>tokens.json</td><td>✅ vigente</td><td>rc-2026-0912</td></tr></table>
</div>

<h2>9. Migas y resultado de búsqueda</h2>
<div class="panel">
  <div class="crumbs-demo"><button class="btn" style="font-size:.75rem;padding:.1rem .45rem">‹</button>
  <button class="btn" style="font-size:.75rem;padding:.1rem .45rem">›</button>
  <span style="width:1px;height:14px;background:var(--panel-bd)"></span>
  Inicio <span style="color:var(--sub)">/</span> <b>Arquitectura</b></div>
  <div style="height:.7rem"></div>
  <div class="qr-demo"><span class="qc">Arquitectura</span><br>Decisiones ADR — <b>rebrand</b> a tokens</div>
  <div class="qr-demo"><span class="qc">Docs</span><br>User stories — criterios <b>Given/When/Then</b></div>
</div>

<h2>10. Código</h2>
<div class="panel"><pre class="demo">python design_tokens.py --check
# design_tokens OK v{design_tokens.version()} — estructura, paridad y 19 pares AA en verde</pre></div>

<h2>11. Los cuatro estados (contrato)</h2>
<div class="panel grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">
  <div class="state loading"><div class="spinner"></div> Cargando documento…</div>
  <div class="state empty">Documento sin contenido todavía.</div>
  <div class="state error"><b>Error al cargar.</b> El índice no responde.
  <div class="row" style="margin-top:.5rem"><button class="btn btn-primary" style="font-size:.78rem">Reintentar</button></div></div>
  <div class="state success"><b>Listo.</b> 291 checks en verde · recibo vigente.</div>
</div>

<h2>12. Atajos (PANT-04)</h2>
<div class="panel">
  <kbd>Ctrl</kbd>+<kbd>K</kbd> buscar · <kbd>/</kbd> buscar · <kbd>Esc</kbd> cerrar ·
  <kbd>A−</kbd>/<kbd>A+</kbd> zoom · <kbd>☰</kbd> colapsar
</div>
</div>
<script>
(function(){{
  var b=document.getElementById('themebtn');
  function saved(){{try{{return localStorage.getItem('dir-tema');}}catch(e){{return null;}}}}
  function apply(t){{document.documentElement.setAttribute('data-theme',t||'oscuro');
    b.textContent=(t==='claro')?'🌙 Tema':'🌞 Tema';}}
  var params=new URLSearchParams(location.search);
  var q=params.get('tema'); if(q) apply(q);
  else apply(saved()||'oscuro');
  b.addEventListener('click',function(){{
    var t=document.documentElement.getAttribute('data-theme')==='claro'?'oscuro':'claro';
    try{{localStorage.setItem('dir-tema',t);}}catch(e){{}} apply(t);}});
}})();
</script>
</body>
</html>"""
    return page


def main() -> int:
    OUT.write_text(build(), encoding="utf-8")
    print(f"styleguide generado: {OUT} (v{design_tokens.version()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
