import sys, nbformat
nb = nbformat.read(sys.argv[1], as_version=4)
for c in nb.cells:
    if c.cell_type == 'code':
        for o in c.outputs:
            t = o.get('text') or o.get('data', {}).get('text/plain') or (o.get('ename', '') + ': ' + o.get('evalue', '') if o.get('ename') else None)
            if t: print(str(t)[:1500])
