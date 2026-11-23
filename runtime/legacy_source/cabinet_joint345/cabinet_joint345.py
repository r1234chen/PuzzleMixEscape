from pathlib import Path
import ast, hashlib

def install(E):
    if getattr(E, '_cabinet_joint342_installed', False):
        return
    p = Path(__file__).with_name('cabinet_methods345.py')
    assert hashlib.sha256(p.read_bytes()).hexdigest() == '26d09c80ca04f9ccee6d1eb4224e4ad4eb409abbf357971e265716b5f4e212fb'
    cls = next((n for n in ast.parse(p.read_text('utf8')).body if isinstance(n, ast.ClassDef) and n.name == 'Escape'))
    nodes = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'is_open', '_is_open_pristine342'}]
    assert len(nodes) == 2
    ns = E.Escape.is_open.__globals__
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec'), ns)
    for n in nodes:
        setattr(E.Escape, n.name, ns[n.name])
    E._cabinet_joint342_installed = True
