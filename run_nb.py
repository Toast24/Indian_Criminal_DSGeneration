import sys, nbformat
from nbclient import NotebookClient
nb = nbformat.read('exp2_caste_bail.ipynb', as_version=4)
try:
    NotebookClient(nb, timeout=None, kernel_name='python3', resources={'metadata': {'path': '.'}}).execute()
finally:
    nbformat.write(nb, sys.argv[1])
