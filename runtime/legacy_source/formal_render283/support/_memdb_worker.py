import json
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
import chromadb
t0 = time.time()
client = chromadb.EphemeralClient()
col = client.create_collection('escape-memory', metadata={'hnsw:space': 'cosine'})
col.add(ids=['warmup'], documents=['warm up the embedding model'])
col.delete(ids=['warmup'])
print(f'MEMDB_READY load {time.time() - t0:.0f}s', flush=True)
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
        op = req.get('op')
        if op == 'reset':
            client.delete_collection('escape-memory')
            col = client.create_collection('escape-memory', metadata={'hnsw:space': 'cosine'})
            out = {'ok': True}
        elif op == 'add':
            items = req.get('items') or []
            if items:
                col.upsert(ids=[str(i['id']) for i in items], documents=[str(i['text']) for i in items])
            out = {'ok': True, 'count': col.count()}
        elif op == 'query':
            n = col.count()
            if n == 0:
                out = {'ok': True, 'ids': [], 'distances': []}
            else:
                r = col.query(query_texts=[str(req.get('text') or '')], n_results=min(int(req.get('k') or 8), n))
                out = {'ok': True, 'ids': r['ids'][0], 'distances': [round(float(x), 4) for x in r['distances'][0]]}
        else:
            out = {'ok': False, 'error': f'unknown op {op}'}
    except Exception as exc:
        out = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
    print('MEMDB_JSON ' + json.dumps(out), flush=True)
