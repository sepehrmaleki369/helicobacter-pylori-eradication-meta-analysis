"""Run an analysis script in an isolated, portable working directory.

Only the original workstation path prefix is substituted in memory. Scientific
code remains unchanged, including the limitations described in the release
notes. Each run copies frozen inputs; outputs never overwrite published inputs.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = '/Users/sepehrmaleki/Documents/spring 2026/helico pilouri'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('script', help='Analysis script filename, e.g. 07c_bayesian_hierarchical.py')
    parser.add_argument('--work-dir', required=True, type=Path, help='New directory for copied inputs and outputs')
    parser.add_argument('--prepare-only', action='store_true', help='Check paths and copy inputs without fitting models')
    parser.add_argument('--source-pdfs', type=Path, help='Optional privately obtained primary-report PDFs')
    args = parser.parse_args()
    if Path(args.script).name != args.script:
        parser.error('Pass a filename from scripts/, not an arbitrary path.')
    source = ROOT / 'scripts' / args.script
    if not source.is_file() or not args.script.startswith(('01_', '02_', '03_', '03b_', '03c_', '04_', '05_', '06_', '06b_', '07_', '07b_', '07c_', '07d_', '07e_', '07f_', '07g_', '08_', '09_', '10_', '10b_')):
        parser.error('Select an analysis script; manuscript exporters need the separately maintained manuscript.')
    work = args.work_dir.resolve()
    if work.exists():
        parser.error('Use a new working directory so existing results cannot be overwritten.')
    work.mkdir(parents=True)
    for src, dest in [('data', 'project/data/processed'), ('models', 'project/models'), ('verification', 'verification')]:
        shutil.copytree(ROOT / src, work / dest)
    for folder in ['project/report', 'project/figures/MAIN_FIGURES', 'project/data/raw_text', 'papers_29_79']:
        (work / folder).mkdir(parents=True, exist_ok=True)
    workbook = ROOT / 'verification/03_rating_template--Final.xlsx'
    if workbook.exists():
        shutil.copy2(workbook, work / workbook.name)
    if args.source_pdfs:
        if not args.source_pdfs.is_dir():
            parser.error('--source-pdfs must name an existing directory.')
        for p in args.source_pdfs.glob('*.pdf'):
            shutil.copy2(p, work / 'papers_29_79' / p.name)
    code = source.read_text().replace(LEGACY_ROOT, str(work))
    compile(code, str(source), 'exec')
    assert LEGACY_ROOT not in code
    (work / 'run_provenance.json').write_text(json.dumps({
        'script': args.script, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'frozen_inputs_copied': True, 'path_substitution_only': True,
        'prepare_only': args.prepare_only, 'work_directory': str(work),
        'status': 'prepared; no model executed' if args.prepare_only else 'execution starting',
        'warning': 'Historical methods retain known validation and data-consistency limitations; this does not establish full reproduction.'
    }, indent=2) + '\n')
    print('Prepared isolated run:', work, flush=True)
    if args.prepare_only:
        return
    if args.script.startswith(('01_', '02_')):
        raise SystemExit('Source extraction needs original PDFs/text; follow docs/REPRODUCIBILITY.md before running it.')
    exec(compile(code, str(source), 'exec'), {'__name__': '__main__', '__file__': str(source)})


if __name__ == '__main__':
    main()
