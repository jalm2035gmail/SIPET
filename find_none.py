import sys, os, json
sys.path.insert(0, '.')
os.environ.setdefault('SQLITE_DB_PATH', 'strategic_planning_development.db')

src = open('fastapi_modulo/modulos/empleados/controladores/departamentos.py', encoding='utf-8').read()
marker_start = '\n    content = """\n'
marker_end = '\n"""\n    content = content.replace'
start = src.find(marker_start) + len(marker_start)
end = src.find(marker_end)
raw_content = src[start:end]

from fastapi_modulo.modulos.empleados.controladores.departamentos import _get_departamentos_catalog
areas = _get_departamentos_catalog()
content = raw_content.replace("__INITIAL_AREAS__", json.dumps(areas, ensure_ascii=False))

MAIN = open('fastapi_modulo/templates/MAIN.html', encoding='utf-8').read()
full = MAIN.replace('{{ content|safe }}', content)

lines = full.split('\n')
print("Total lines in rendered page:", len(lines))

for i, line in enumerate(lines):
    idx = 0
    while idx < len(line):
        pos = line.find('none', idx)
        if pos == -1:
            break
        idx = pos + 1
        before = line[pos-1] if pos > 0 else ' '
        after = line[pos+4] if pos+4 < len(line) else ' '
        bad_before = before.isalnum() or before in '_-"\''
        bad_after = after.isalnum() or after in '_-"\''
        if bad_before or bad_after:
            continue
        # skip CSS-value context
        ctx = line[max(0, pos-30):pos+30]
        if ':' in ctx or 'display' in ctx or 'overflow' in ctx:
            continue
        print("L%d col%d: %r" % (i+1, pos, line[max(0, pos-40):pos+60]))
