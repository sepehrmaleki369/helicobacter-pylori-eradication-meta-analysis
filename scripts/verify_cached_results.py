"""Verify packaged artifacts and saved metrics without changing data or fitting.

Exit 2 means artifact/metric verification passed but unresolved data consistency
issues remain. This is intentionally not a claim of successful fresh fitting.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys
import numpy as np
from scipy.stats import norm
from sklearn.metrics import brier_score_loss, r2_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'release_manifest.json').read_text())
    for name, info in manifest['files'].items():
        p = ROOT / name
        assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == info['sha256'], name
    with (ROOT / 'data/clean_dataset.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    y = np.array([float(r['ITT_Rate']) for r in rows])
    groups = np.array([int(r['Ref']) for r in rows])
    n = np.array([int(float(r['N_ITT'])) for r in rows])
    assert len(rows) == 140 and len(set(groups)) == 60 and n.sum() == 17887
    assert len({(r['Ref'], r['Arm_Label']) for r in rows}) == len(rows)
    assert np.all((y >= 0) & (y <= 100)) and np.all(n > 0)
    np.testing.assert_array_equal(y, np.load(ROOT / 'models/y_reg_pretreat.npy', allow_pickle=False))
    np.testing.assert_array_equal(groups, np.load(ROOT / 'models/g_reg_pretreat.npy', allow_pickle=False))
    saved = json.loads((ROOT / 'reports/prediction_reporting_2026-11-02.json').read_text())
    checked = 0
    for model, schemes in saved['models'].items():
        for cv in ('loo', 'loso'):
            pred = np.load(ROOT / 'models' / f'{model}_{cv}_ypred.npy', allow_pickle=False)
            assert pred.shape == y.shape and np.isfinite(pred).all()
            values = {'r2': float(r2_score(y, pred)), 'rmse_pp': float(np.sqrt(np.mean((y-pred)**2)))}
            for threshold in (85, 90):
                actual = (y >= threshold).astype(int)
                values[f'auc{threshold}'] = float(roc_auc_score(actual, pred))
                values[f'brier{threshold}'] = float(brier_score_loss(actual, norm.sf(threshold, loc=pred, scale=10)))
            for metric, value in values.items():
                np.testing.assert_allclose(value, schemes[cv][metric], rtol=0, atol=1e-12)
                checked += 1
    issues = []
    for r in rows:
        expected_count = round(float(r['ITT_Rate']) * float(r['N_ITT']) / 100)
        if expected_count != float(r['Successes_ITT']):
            issues.append({'Ref': r['Ref'], 'Arm_Label': r['Arm_Label'], 'field': 'Successes_ITT',
                           'stored': r['Successes_ITT'], 'derived_from_current_fields': expected_count})
        if abs(float(r['ITT_Prop']) - float(r['ITT_Rate'])/100) > 1e-9:
            issues.append({'Ref': r['Ref'], 'Arm_Label': r['Arm_Label'], 'field': 'ITT_Prop',
                           'stored': r['ITT_Prop'], 'derived_from_current_fields': float(r['ITT_Rate'])/100})
    result = {'artifact_integrity_passed': True, 'cached_nonbayesian_metrics_checked': checked,
              'cached_metrics_match_saved_audit': True, 'arms': len(y), 'studies': len(set(groups)),
              'patients': int(n.sum()), 'data_consistency_passed': not issues,
              'unresolved_derived_field_issues': issues,
              'data_changed': False, 'models_refitted': False, 'fresh_fit_reproduction_established': False,
              'manuscript_submission_ready': False}
    if args.report:
        args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 2 if issues else 0


if __name__ == '__main__':
    sys.exit(main())
