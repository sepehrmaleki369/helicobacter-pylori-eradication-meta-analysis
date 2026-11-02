"""Check data, table cells, provenance and known wording errors without refitting.

A passing audit verifies only the listed evidence checks. It does not resolve
missing search history, eligibility decisions, author roles or validation gaps.
"""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re
import numpy as np
from scipy.stats import norm
from sklearn.metrics import brier_score_loss, r2_score, roc_auc_score
from PIL import Image

BASE=Path(__file__).resolve().parents[2]
DATE='2026-11-02'
NAMES={'elasticnet':'ElasticNet','randomforest':'RandomForest','gradientboost':'GradientBoost',
       'xgboost':'XGBoost','lightgbm':'LightGBM','gaussianprocess':'Gaussian Process'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(y,pred):
    result={'r2':float(r2_score(y,pred)),
            'rmse_pp':float(np.sqrt(np.mean((y-pred)**2)))}
    for t in (85,90):
        actual=(y>=t).astype(int)
        result[f'auc{t}']=float(roc_auc_score(actual,pred))
        result[f'brier{t}']=float(brier_score_loss(actual,1-norm.cdf((t-pred)/10)))
    return result


def read_table(text,label):
    table=next(b for b in re.findall(r'\\begin\{table\}.*?\\end\{table\}',text,re.S)
               if f'\\label{{tab:{label}}}' in b)
    rows={}
    for line in table.splitlines():
        line=line.strip()
        if '&' not in line or not line.endswith(r'\\'):continue
        cells=[c.strip() for c in line[:-2].split('&')]
        if cells[0] in [*NAMES.values(),'Bayesian hierarchical (LOO only)']:
            assert cells[0] not in rows
            rows[cells[0]]=[None if c=='---' else float(c.replace('$-$','-').replace('$','')) for c in cells[1:]]
        assert not cells[0].startswith(('BART',r'\textbf{Bayesian'))
    return rows


def main():
    dataset=BASE/'project/data/processed/clean_dataset.csv'
    rows=list(csv.DictReader(dataset.open()))
    y=np.array([float(r['ITT_Rate']) for r in rows]);g=np.array([int(r['Ref']) for r in rows])
    manifest=json.loads((BASE/f'project/report/prediction_reporting_{DATE}.json').read_text())
    protected=json.loads((BASE/f'paper/revision_history/{DATE}_protected_inputs.json').read_text())
    assert sha(dataset)==manifest['dataset_sha256']
    assert sha(BASE/manifest['source_script'])==manifest['source_script_sha256']
    for filename,expected in {**protected,**manifest['input_hashes']}.items():
        assert sha(BASE/filename)==expected,f'Analytical input changed: {filename}'
    np.testing.assert_array_equal(y,np.load(BASE/'project/models/y_reg_pretreat.npy'))
    np.testing.assert_array_equal(g,np.load(BASE/'project/models/g_reg_pretreat.npy'))
    computed={}
    for key in NAMES:
        computed[key]={}
        for cv in ('loo','loso'):
            pred=np.load(BASE/f'project/models/{key}_{cv}_ypred.npy')
            assert pred.shape==y.shape and np.isfinite(pred).all()
            computed[key][cv]=metrics(y,pred)
            for name,value in computed[key][cv].items():
                np.testing.assert_allclose(value,manifest['models'][key][cv][name],atol=1e-12,rtol=0)
    fallback={}
    for cv,baseline in [('loo_arm',np.array([np.delete(y,i).mean() for i in range(len(y))])),
                        ('loso',np.array([y[g!=group].mean() for group in g]))]:
        delta=float(np.max(np.abs(np.load(BASE/f'project/models/bart_{cv}_ypred.npy')-baseline)))
        assert delta<1e-10
        fallback[cv]={'maximum_difference_from_fallback':delta,'arms_matching':len(y)}
    bay=metrics(y,np.load(BASE/'project/models/bayes_loo_arm_ypred.npy'))
    report={'date':DATE,'arms':len(rows),'studies':len(set(g)),
            'patients':sum(int(r['N_ITT']) for r in rows),'dataset_sha256':sha(dataset),
            'resistance_sources':dict(Counter(r['Resistance_Source_Type'] for r in rows)),
            'bart_fallback':fallback,'tables':{},'included_citations':{},'prediction_metrics':computed,
            'protected_files_unchanged':len(protected),'checked_table_cells':0,
            'unresolved':['Historical search date/strategies; complete screening of the documented 2 November update',
                          'Screening-stage allocation: 32 excluded records versus 78 reported full texts',
                          '13 arms below the nominal 40-patient threshold and quasi-random Ref 81',
                          'New-author contributions and final manuscript approvals',
                          'Genuine Bayesian LOSO and nested RFE validation unavailable',
                          'Historical missingness flags differ from current missing-value counts']}
    assert (report['studies'],report['arms'],report['patients'])==(60,140,17887)
    assert report['resistance_sources']=={'regional-estimate':100,'in-paper':40}
    report['small_arms']=[{'ref':r['Ref'],'arm':r['Arm_Label'],'n':int(r['N_ITT'])} for r in rows if int(r['N_ITT'])<40]
    assert len(report['small_arms'])==13
    s1=(BASE/'paper/my_version/supp_table_s1.tex').read_text()
    expected=set(re.findall(r'\\cite\{([^}]+)\}',s1));assert len(expected)==60
    study_counts={int(ref):[sum(int(r['Ref'])==ref for r in rows),
                          sum(int(r['N_ITT']) for r in rows if int(r['Ref'])==ref)] for ref in set(g)}
    report['supplementary_study_counts']={}
    for filename in ['paper/my_version/supp_table_s1.tex','paper/supp_table_s1.tex','paper/with rob test/supp_table_s1.tex']:
        source=(BASE/filename).read_text();totals=[0,0];seen=set()
        for line in source.splitlines():
            if not re.match(r'^\d+\s*&',line):continue
            cells=[c.strip() for c in line.split('&')]
            key=re.search(r'\\cite\{([^}]+)\}',line).group(1)
            ref=int(re.search(r'ref(\d+)_',key).group(1)) if key.startswith('ref') else {'chey2022':41,'murakami2016':80,'hu2025':88}[key]
            assert ref not in seen;seen.add(ref)
            counts=[int(cells[3]),int(cells[4].replace(',',''))]
            assert counts==study_counts[ref],(filename,ref,counts,study_counts[ref])
            totals=[a+b for a,b in zip(totals,counts)]
        assert len(seen)==60 and totals==[140,17887]
        report['supplementary_study_counts'][filename]={'studies':len(seen),'arms':totals[0],'patients':totals[1]}
    s2=(BASE/'paper/my_version/supp_table_s2.tex').read_text()
    report['excluded_record_count']=len(re.findall(r'^\d+\s*&',s2,re.M))
    assert report['excluded_record_count']==32
    for filename in ['paper/my_version/main_my_version.tex','paper/main_no_rob.tex','paper/with rob test/main.tex']:
        path=BASE/filename;text=path.read_text()
        if 'my_version' in filename:
            text=re.sub(r'\\input\{([^}]+)\}',lambda m:(path.parent/(m.group(1)+'.tex')).read_text(),text)
        block=re.search(r'\\cite\{(ref29_kim2012.*?)\}',text,re.S).group(1)
        cited=set(re.sub(r'\s+','',block).split(','));assert cited==expected
        report['included_citations'][filename]=len(cited)
        reg=read_table(text,'regression');cls=read_table(text,'classification');assert len(reg)==len(cls)==7
        checked=0
        for key,name in NAMES.items():
            want=[round(computed[key]['loo']['r2'],3),round(computed[key]['loso']['r2'],3),round(computed[key]['loso']['rmse_pp'],2)]
            np.testing.assert_allclose(reg[name],want,atol=1e-12,rtol=0);checked+=3
            want=[round(computed[key][cv][m],2) for cv in ('loo','loso') for m in ('auc85','brier85','auc90','brier90')]
            np.testing.assert_allclose(cls[name],want,atol=1e-12,rtol=0);checked+=8
        name='Bayesian hierarchical (LOO only)'
        assert reg[name]==[round(bay['r2'],3),None,None]
        assert cls[name]==[round(bay[m],2) for m in ('auc85','brier85','auc90','brier90')]+[None]*4
        checked+=11
        for old in ['clinically pre-specified','pre-specified clinical covariate set','pre-specified subgroups',
                    'We pre-specify','we pre-specify','Seven non-Bayesian families','Eight model families were examined',
                    'LOSO $R^2$ between $-0.026$','across the seven comparison families','yield LOO AUC 0.00',
                    'Studies excluded at full-text review with reasons','Full search strings are reproduced in Supplementary']:
            assert old not in text,(filename,old)
        assert 'same six pairs of cached predictions' in text and 'globally selected feature set' in text
        assert 'Genuine\nBayesian LOSO' in text or 'Genuine Bayesian LOSO' in text
        assert 'screening log' in text and '13 arms' in text
        report['tables'][filename]={'cells_checked':checked,'numeric_and_targeted_wording_checks':True}
        report['checked_table_cells']+=checked
    for filename,expected_hash in manifest['figure_hashes'].items():
        path=BASE/'project/figures/MAIN_FIGURES'/filename;assert sha(path)==expected_hash
        with Image.open(path) as image:
            info=image.info;assert info['Dataset']=='140 arms, 60 studies'
            assert '142 arms' not in str(info)
            if filename=='Fig4_calibration.png':assert 'apparent' in info['Description'] and 'LOSO' in info['Description']
            elif filename=='SuppFig_models_comparison.png':assert 'BART excluded' in info['Description']
            else:assert 'Provisional' in info['Description']
    out=BASE/f'paper/MANUSCRIPT_AUDIT_{DATE}.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Checked {len(protected)} unchanged analytical inputs; 60 studies, 140 arms, 17,887 patients.')
    print(f'Checked {report["checked_table_cells"]} prediction-table cells, every supplementary study count, 60 citations per version, wording and figure provenance.')
    print(f'Evidence checks passed; {len(report["unresolved"])} unresolved items remain. Report: {out}')


if __name__=='__main__':main()
