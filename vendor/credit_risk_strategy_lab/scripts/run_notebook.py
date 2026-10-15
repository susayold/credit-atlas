"""Execute source notebook top-to-bottom; save outputs privately, never overwrite source."""
import json
import sys
import uuid
import argparse
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--notebook',default='00_source_qualification.ipynb')
args=parser.parse_args()
source=(root/'notebooks'/args.notebook).resolve()
if source.parent != (root/'notebooks').resolve() or source.suffix!='.ipynb':
    raise ValueError('Select a source notebook within the project notebooks directory')
notebook = nbformat.read(source, as_version=4)
nbformat.validate(notebook)
manager = KernelManager(kernel_name='python3')
manager.ip = '127.0.0.1'
manager.kernel_spec.argv[0] = sys.executable
client = NotebookClient(notebook, km=manager, timeout=60,
                        resources={'metadata': {'path': str(root)}})
try:
    client.execute()
finally:
    if manager.has_kernel:
        manager.shutdown_kernel(now=True)
nbformat.validate(notebook)
target = root/'artifacts/private/notebook-runs'/uuid.uuid4().hex
target.mkdir(parents=True, exist_ok=False)
executed_path=target/(source.stem+'.executed.ipynb')
nbformat.write(notebook, executed_path)
executed = [cell for cell in notebook.cells if cell.cell_type == 'code']
assert all(cell.execution_count is not None for cell in executed)
assert not any(output.output_type == 'error' for cell in executed for output in cell.outputs)
print(json.dumps({'status':'PASS', 'executed_code_cells':len(executed),
                  'output':str(executed_path)}, indent=2))
