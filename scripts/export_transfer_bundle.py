"""Create a checksummed, platform-neutral project bundle. Samples are optional."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DIRS=('.github','catalog','configs','docs','evidence','plans','reports','scripts','src','tests','deliverables')
FILES=('README.md','LICENSE','PRODUCT.md','DESIGN.md','pyproject.toml','uv.lock','.python-version','.gitattributes','.gitignore')


def export(output,include_samples=False):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    paths=[]
    for name in DIRS:
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.zip') and not p.name.startswith('.~') and not p.name.endswith('tests.xml') and p!=output)
    paths.extend(ROOT/p for p in FILES if (ROOT/p).is_file())
    if include_samples:paths.extend(p for p in (ROOT/'data/raw').rglob('*') if p.is_file())
    entries={p.relative_to(ROOT).as_posix():p for p in sorted(set(paths))}
    checks={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in entries.items()}
    manifest={'schema':'transfer_bundle_v1','include_samples':include_samples,'note':'Python runtime, OS-specific wheels, model weights and GPU drivers are NOT included. Rebuild the environment on target OS.','sha256':checks}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for name,path in entries.items():z.write(path,name)
        z.writestr('TRANSFER-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        for name,sha in checks.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha
    sha=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(sha+'  '+output.name+'\n')
    print(json.dumps({'bundle':str(output),'bytes':output.stat().st_size,'files':len(entries),'sha256':sha,'includes_samples':include_samples},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('data/transfer/vla-delivery.zip'));p.add_argument('--include-samples',action='store_true');a=p.parse_args();export(a.output,a.include_samples)
