"""Rebuild reporting from one cached prediction set; never fit or overwrite models.

Tables share the six non-Bayesian prediction pairs written by
07g_classification_full.py. The Bayesian LOO-arm file is separate and is
identified as such. BART caches are diagnosed, not treated as fitted BART.
"""
from pathlib import Path
import hashlib
import json
import os
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'hpylori_matplotlib_cache'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import brier_score_loss, r2_score, roc_auc_score

BASE = Path(__file__).resolve().parents[2]
MODELS = BASE/'project/models'
FIG = BASE/'project/figures/MAIN_FIGURES'
PAPER = BASE/'paper/my_version'
DATE = '2026-11-02'
NAMES = {'elasticnet': 'ElasticNet', 'randomforest': 'RandomForest',
         'gradientboost': 'GradientBoost', 'xgboost': 'XGBoost',
         'lightgbm': 'LightGBM', 'gaussianprocess': 'Gaussian Process'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(y, pred):
    slope, intercept_pp = np.polyfit(pred, y, 1)
    result = {'r2': float(r2_score(y, pred)),
              'rmse_pp': float(np.sqrt(np.mean((y-pred)**2))),
              'slope': float(slope), 'intercept_proportion': float(intercept_pp/100),
              'mse_proportion': float(np.mean(((y-pred)/100)**2))}
    for threshold in (85, 90):
        outcome = (y >= threshold).astype(int)
        result[f'auc{threshold}'] = float(roc_auc_score(outcome, pred))
        result[f'brier{threshold}'] = float(brier_score_loss(
            outcome, norm.sf(threshold, loc=pred, scale=10)))
    return result


def calibration_panel(ax, y, pred, title, colour, description):
    ax.scatter(pred, y, s=13, alpha=.25, color=colour, edgecolor='none')
    group = pd.qcut(pred, 10, duplicates='drop')
    binned = pd.DataFrame({'prediction': pred, 'observed': y, 'bin': group})
    means = binned.groupby('bin', observed=True)[['prediction', 'observed']].mean()
    ax.plot(means.prediction, means.observed, 'o-', color=colour, lw=1.5,
            markersize=5, label='Decile means')
    ax.plot([20,100], [20,100], '--', color='#697386', lw=1, label='Identity')
    ax.set(xlim=(20,100), ylim=(20,100), xlabel='Predicted eradication (%)',
           ylabel='Observed eradication (%)', title=title)
    ax.text(.04, .96, description, transform=ax.transAxes, va='top', fontsize=9,
            bbox={'facecolor': 'white', 'alpha': .9, 'edgecolor': 'none'})
    ax.grid(alpha=.15)
    ax.legend(loc='lower right', fontsize=8, frameon=False)


def main():
    source = BASE/'project/data/processed/clean_dataset.csv'
    frame = pd.read_csv(source).dropna(subset=['ITT_Rate', 'N_ITT', 'Successes_ITT']).reset_index(drop=True)
    y = frame.ITT_Rate.to_numpy(float)
    groups = frame.Ref.to_numpy(int)
    np.testing.assert_array_equal(y, np.load(MODELS/'y_reg_pretreat.npy'))
    np.testing.assert_array_equal(groups, np.load(MODELS/'g_reg_pretreat.npy'))
    report = {'date': DATE, 'arms': len(y), 'studies': int(frame.Ref.nunique()),
              'dataset_sha256': sha(source), 'source_script': 'project/scripts/07g_classification_full.py',
              'source_script_sha256': sha(BASE/'project/scripts/07g_classification_full.py'),
              'evaluation': 'Cached predictions; no fresh model refits; fold provenance inferred from saved script, not per-fold logs',
              'thresholds': {'values_percent': [85,90], 'purpose': 'exploratory operational targets, not a claim of guideline-defined categories',
                             'probability_transform': 'normal survival function, fixed SD=10 percentage points'},
              'models': {}, 'input_hashes': {}, 'bart_fallback_diagnostics': {}}
    predictions = {}
    for key, name in NAMES.items():
        report['models'][key] = {'name': name}
        predictions[key] = {}
        for cv in ('loo','loso'):
            path = MODELS/f'{key}_{cv}_ypred.npy'
            pred = np.load(path)
            assert pred.shape == y.shape and np.isfinite(pred).all(), path
            report['input_hashes'][str(path.relative_to(BASE))] = sha(path)
            report['models'][key][cv] = metrics(y, pred)
            predictions[key][cv] = pred
    order = sorted(NAMES, key=lambda key: -report['models'][key]['loso']['r2'])
    report['table_order'] = order
    for cv, expected in [('loo_arm', np.array([np.delete(y,i).mean() for i in range(len(y))])),
                         ('loso', np.array([y[groups!=g].mean() for g in groups]))]:
        path = MODELS/f'bart_{cv}_ypred.npy'
        saved = np.load(path)
        delta = float(np.max(np.abs(saved-expected)))
        assert delta < 1e-10, 'BART cache changed; re-examine exclusion'
        report['input_hashes'][str(path.relative_to(BASE))] = sha(path)
        report['bart_fallback_diagnostics'][cv] = {
            'maximum_difference_from_training_mean': delta,
            'matching_arms': int(np.sum(np.isclose(saved,expected,rtol=0,atol=1e-10))),
            'excluded_from_model_comparison': True}
    for key, filename, factor in [('loo','bayes_loo_arm_ypred.npy',1),
                                  ('apparent','bayes_marginal_ypred.npy',100)]:
        path = MODELS/filename
        report['input_hashes'][str(path.relative_to(BASE))] = sha(path)
        report.setdefault('bayesian',{})[key] = metrics(y,np.load(path)*factor)
    report['bayesian']['loso'] = None
    report['bayesian']['caveats'] = 'LOO retains same-study information and global preprocessing; apparent predictions are fitted on all arms with intercept zero'

    # Both tables below consume exactly the same six cached prediction pairs.
    reg = [r'\begin{table}[!htbp]',r'\centering',
           r'\caption{Regression performance recomputed from the same cached prediction pairs used for threshold classification. Six non-Bayesian models use 39 predictors and are ordered by LOSO $R^2$. RMSE is in percentage points (pp). Bayesian LOO-arm results come from a separate refit with global preprocessing and possible same-study information; genuine Bayesian LOSO is unavailable. BART is excluded because its cached predictions match the fallback training means.}',
           r'\label{tab:regression}',r'\small',r'\begin{tabular}{lrrr}',r'\toprule',
           r'Model & LOO $R^2$ & LOSO $R^2$ & LOSO RMSE (pp) \\',r'\midrule']
    for key in order:
        m = report['models'][key]
        reg.append(f"{m['name']} & {m['loo']['r2']:+.3f} & {m['loso']['r2']:+.3f} & {m['loso']['rmse_pp']:.2f}" + r' \\')
    reg += [r'\midrule',f"Bayesian hierarchical (LOO only) & {report['bayesian']['loo']['r2']:+.3f} & --- & ---" + r' \\',
            r'\bottomrule',r'\end{tabular}',r'\end{table}','']
    (PAPER/'table_2_regression.tex').write_text('\n'.join(reg))
    cls = [r'\begin{table}[!htbp]',r'\centering',
           r'\caption{Exploratory classification at 85\% and 90\% eradication targets. Non-Bayesian results use the identical cached prediction pairs as Table~\ref{tab:regression}. The probability transformation assumes a residual SD of ten percentage points. Bayesian LOO is shown separately with its validation limitations; Bayesian LOSO is unavailable. Failed BART fits are excluded.}',
           r'\label{tab:classification}',r'\scriptsize',r'\begin{tabular}{lrrrrrrrr}',r'\toprule',
           r'& \multicolumn{4}{c}{LOO (held-out arm)} & \multicolumn{4}{c}{LOSO (held-out study)} \\',
           r'\cmidrule(lr){2-5} \cmidrule(lr){6-9}',
           r'& \multicolumn{2}{c}{$\geq$85\%} & \multicolumn{2}{c}{$\geq$90\%} & \multicolumn{2}{c}{$\geq$85\%} & \multicolumn{2}{c}{$\geq$90\%} \\',
           r'Model & AUC & Brier & AUC & Brier & AUC & Brier & AUC & Brier \\',r'\midrule']
    for key in order:
        values=[report['models'][key][cv][metric] for cv in ('loo','loso') for metric in ('auc85','brier85','auc90','brier90')]
        cls.append(NAMES[key]+' & '+' & '.join(f'{v:.2f}' for v in values)+r' \\')
    values=[report['bayesian']['loo'][metric] for metric in ('auc85','brier85','auc90','brier90')]
    cls += [r'\midrule','Bayesian hierarchical (LOO only) & '+' & '.join(f'{v:.2f}' for v in values)+r' & --- & --- & --- & --- \\',
            r'\bottomrule',r'\end{tabular}',r'\end{table}','']
    (PAPER/'table_3_classification.tex').write_text('\n'.join(cls))

    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(1,2,figsize=(11,4.7),layout='constrained')
    b=report['bayesian']['apparent']
    calibration_panel(axes[0],y,np.load(MODELS/'bayes_marginal_ypred.npy')*100,
        'A. Bayesian: full-cohort apparent fit','#7657a7',
        f"Study intercepts set to zero\nNo held-out studies\nSlope {b['slope']:.3f}")
    m=report['models']['gaussianprocess']['loso']
    calibration_panel(axes[1],y,predictions['gaussianprocess']['loso'],
        'B. Gaussian Process: LOSO predictions','#247e88',
        f"Studies held out during fitting\nSlope {m['slope']:.3f}")
    fig.suptitle('Calibration shown separately by evaluation scheme',fontsize=12)
    fig.savefig(FIG/'Fig4_calibration.png',dpi=180,metadata={
        'Description':'Bayesian full-cohort apparent fit in panel A; Gaussian Process LOSO in panel B; not a like-for-like validation comparison',
        'Dataset':f'{len(y)} arms, {frame.Ref.nunique()} studies'})
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True,layout='constrained')
    labels=[NAMES[key] for key in order]
    for ax,cv,title,color in zip(axes,['loo','loso'],['LOO-arm','LOSO-study'],['#5b70a6','#247e88']):
        values=[report['models'][key][cv]['r2'] for key in order]
        ax.barh(np.arange(len(order)),values,color=color)
        ax.axvline(0,color='#394454',lw=.8)
        ax.set_yticks(np.arange(len(order)),labels)
        ax.set_xlim(-.16,.40);ax.set_xlabel('R²');ax.set_title(title)
        ax.grid(axis='x',alpha=.15)
        for i,value in enumerate(values):
            ax.text(value+(.008 if value>=0 else -.008),i,f'{value:+.3f}',
                    va='center',ha='left' if value>=0 else 'right',fontsize=9)
    axes[0].invert_yaxis()
    fig.suptitle(f'Six non-Bayesian models · {len(y)} arms · {frame.Ref.nunique()} studies',fontsize=12)
    fig.savefig(FIG/'SuppFig_models_comparison.png',dpi=180,metadata={
        'Description':'Six non-Bayesian models; same cached prediction pairs as Tables 2 and 3; BART excluded; Bayesian LOSO unavailable',
        'Dataset':f'{len(y)} arms, {frame.Ref.nunique()} studies'})
    plt.close(fig)
    # Keep unknown screening allocations explicit instead of inventing a flow.
    fig,ax=plt.subplots(figsize=(10,8),layout='constrained')
    ax.set(xlim=(0,10),ylim=(0,10));ax.axis('off')
    def box(x,y,text,colour='#edf2f7',size=10):
        ax.text(x,y,text,ha='center',va='center',fontsize=size,
                bbox={'boxstyle':'round,pad=.8','facecolor':colour,'edgecolor':'#768396'})
    box(2.5,8.7,'Seed network meta-analysis\n51 records reported')
    box(7.5,8.7,'Five supplementary PubMed searches\n45 records reported\nFinal search date unconfirmed')
    box(5,6.9,'Historical identification totals\n96 records; 4 duplicates removed; 92 screened\nNot independently reconciled')
    box(5,4.5,'Screening-stage allocation unresolved\nEarlier draft: 78 full texts\nSupplementary Table S2: 32 excluded records\nOriginal screening log needed','#fff1d8',11)
    box(5,1.9,'Verified final analytic cohort\n60 studies · 140 arms · 17,887 patients','#dff0e9',12)
    for start,end in [((2.5,8.1),(4.4,7.5)),((7.5,7.9),(5.6,7.5)),
                      ((5,6.2),(5,5.5)),((5,3.4),(5,2.7))]:
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#768396'})
    fig.suptitle('Provisional study-selection summary — reconciliation required',fontsize=13)
    fig.savefig(FIG/'Fig1_PRISMA.png',dpi=180,metadata={
        'Description':'Provisional summary, not a reconciled PRISMA flow; historical screening-stage totals unverified',
        'Dataset':f'{len(y)} arms, {frame.Ref.nunique()} studies'})
    plt.close(fig)
    for filename in ('Fig1_PRISMA.png','Fig4_calibration.png','SuppFig_models_comparison.png'):
        report.setdefault('figure_hashes',{})[filename]=sha(FIG/filename)
    output=BASE/f'project/report/prediction_reporting_{DATE}.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    pd.DataFrame([{'model':NAMES[key],'scheme':cv,**report['models'][key][cv]}
                  for key in order for cv in ('loo','loso')]).to_csv(
                      BASE/f'project/report/prediction_reporting_{DATE}.csv',index=False)
    print('Rebuilt both tables, two prediction figures and the provisional selection summary.')
    print('BART training-mean fallback confirmed in every arm; excluded.')
    for key in order:
        m=report['models'][key]['loso']; print(f"{NAMES[key]}: LOSO R2={m['r2']:+.6f}, RMSE={m['rmse_pp']:.6f} pp")


if __name__=='__main__':
    main()
