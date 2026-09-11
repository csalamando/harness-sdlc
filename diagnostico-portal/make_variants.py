"""Genera variantes del index.html copiado para capturar estados de UI."""
import pathlib

src = pathlib.Path("portal/index.html").read_text(encoding="utf-8")

def variant(name, extra_js):
    inject = f"<script>window.addEventListener('load',function(){{setTimeout(function(){{{extra_js}}},400);}});</script>"
    out = src.replace("</body>", inject + "\n</body>")
    pathlib.Path(f"portal/{name}.html").write_text(out, encoding="utf-8")

# 1. menú colapsado (side-off)
variant("v-colapsado", "document.getElementById('btn-side').click();")
# 2. tema claro
variant("v-claro", "if(document.documentElement.dataset.theme!=='claro')document.getElementById('btn-tema').click();")
# 3. búsqueda abierta con resultados
variant("v-busqueda", "var q=document.getElementById('q');q.focus();q.value='sprint';q.dispatchEvent(new Event('input'));")
# 4. zoom A+ aplicado dos veces (demostrar que el menú no escala)
variant("v-zoom", "document.getElementById('btn-zmas').click();document.getElementById('btn-zmas').click();")
# 5. ayuda abierta
variant("v-ayuda", "document.getElementById('btn-help').click();")
print("variantes listas")
