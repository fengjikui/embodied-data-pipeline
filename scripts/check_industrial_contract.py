"""Inspect intake documents; exit 2 for blockers. Never connects to a robot."""
import argparse
import json
from pathlib import Path
from vla_pipeline.industrial_contract import audit_contract
from vla_pipeline.io import write_json

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--evidence-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError('Use a fresh audit output')
    result = audit_contract(json.loads(a.contract.read_text(encoding='utf-8')), a.evidence_root)
    write_json(a.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['document_checks_passed'] else 2)
