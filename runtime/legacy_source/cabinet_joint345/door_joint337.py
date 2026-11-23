from pathlib import Path
import ast, hashlib

def install(E):
    if getattr(E, '_door_joint337_installed', False):
        return
    p = Path(__file__).with_name('door_methods337.py')
    assert hashlib.sha256(p.read_bytes()).hexdigest() == '0365cd51ab2101e82e9b40ace2e911c1c567826e47483ecdb2397f026bfe8d58'
    tree = ast.parse(p.read_text('utf8'))
    names = {'_door_swing', '_door_live_state337'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(nodes) == 2
    ns = E.Escape._door_swing.__globals__
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec'), ns)
    for name in names:
        setattr(E.Escape, name, ns[name])
    E._door_joint337_installed = True
