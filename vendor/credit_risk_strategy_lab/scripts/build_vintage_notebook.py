"""Generate the B11 private-input notebook; keep source cells free of real outputs."""
from pathlib import Path
import nbformat as nbf

root=Path(__file__).resolve().parents[1]
nb=nbf.v4.new_notebook()
md=nbf.v4.new_markdown_cell
code=nbf.v4.new_code_cell
nb.cells=[
md('''# 02 — Vintage and competing-event incidence
## tl;dr
This notebook evaluates the authorized 2012 annual sample at aligned observation
ages. Its executed summary below reports measured outcomes, not model predictions.
Only one origination vintage is available: segment differences cannot establish
which origination year is worse, or the causal effect of a refinance program.
'''),
md('''## Context & Methods
Decision: determine whether apparent credit-performance differences survive
alignment on observation age, eligibility and competing exits before using them
in underwriting research. Audience: a credit-risk reviewer and portfolio recruiter.
### Key Assumptions
- First observed month is time zero; only the existing early-entry eligible set enters incidence.
- D3 is numeric delinquency 03–99; REO/other termination is a competing exit, not relabeled D3.
- Aalen–Johansen treats D3, prepayment/maturity and other exit as mutually exclusive first events.
- Unknown/gapped history stops follow-up; identification under censoring needs independent censoring.
- All displayed cohort cells require calendar maturity; no annualization or zero-filled immature cells.
- 95% intervals use 500 IID loan-bootstrap replicates. They exclude shared macro shocks,
  source revisions and selection bias. Sparse-event intervals are exploratory, not significance tests.
- Latest-release retrospective data is not an archived historical point-in-time extract.

References: [Freddie Mac guide](https://www.freddiemac.com/fmac-resources/research/pdf/general_user_guide_july_2026.pdf),
[survival multi-state methods](https://cran.r-project.org/web/packages/survival/vignettes/compete.pdf).
'''),
md('''## Data
### 1. Verify immutable inputs and full source membership
Change the explicit run parameter only to another completed, qualified private run.
Source records and loan identifiers are never printed or embedded in outputs.
'''),
code('''import json
from pathlib import Path
import uuid
import duckdb
from crsl.verify_vintage import verify
root=Path.cwd()
if root.name=='notebooks': root=root.parent
run=root/'artifacts/private/vintage-78feb345a476'
verification=verify(root,run)
summary=json.loads((run/'summary.json').read_text())
manifest=json.loads((run/'run-complete.json').read_text())
print('Source identity checks:',len(verification['horizon_membership_checks']))
print('Curve rows independently checked:',verification['curves_checked'])
print('Evidence:',manifest['evidence_class'],'; source:',manifest['canonical_run'])
assert all(r['origination_year']==2012 for r in summary['cohorts']), 'Revise single-vintage narrative for expanded data'
figures=root/'artifacts/private/notebook-figures'/uuid.uuid4().hex
figures.mkdir(parents=True,exist_ok=False)
'''),
md('''### 2. Measured headline and exclusions
The denominator is fixed at eligible loans, not only surviving balances or known
binary labels. Other exits remain in competing-event incidence, while the baseline
binary-label dataset separately treats them as unavailable.
'''),
code('''overall=[r for r in summary['horizons'] if r['segment']=='all']
for r in overall:
    print(f"{r['observation_age']:2d}m | eligible={r['eligible_loans']:,} | excluded={r['excluded_loans']:,} "
          f"| first D3={r['observed_d3_count']:,} | incidence={r['cif_d3']:.3%} "
          f"| 95% interval [{r['ci_lower']:.3%}, {r['ci_upper']:.3%}] "
          f"| unknown follow-up={r['unknown_before_horizon']:,}")
print('At-risk counts (before the horizon-month event):',[(r['observation_age'],r['at_risk']) for r in overall])
'''),
md('''## Results
### 3. First-event incidence and the shrinking risk set
Lines show within-2012 segments, not separate origination vintages. The risk-set
panel helps distinguish a low current event count from a low cumulative probability.
'''),
code('''import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.titleweight':'bold','figure.dpi':110})
styles={'all':('All eligible','#1f5b99','-'), 'relief':('Relief refinance','#a06e00','--'),
        'non_relief':('Non-relief','#525252',':')}
fig,axes=plt.subplots(1,2,figsize=(12,4.4),layout='constrained')
for segment,(label,color,line) in styles.items():
    rows=[r for r in summary['curves'] if r['segment']==segment]
    axes[0].plot([r['observation_age'] for r in rows],[r['cif_d3'] for r in rows],label=label,color=color,linestyle=line,lw=2)
    axes[1].plot([r['observation_age'] for r in rows],[r['at_risk'] for r in rows],label=label,color=color,linestyle=line,lw=2)
axes[0].set_title('2012 sample: first numeric-D3 incidence')
axes[0].set_ylabel('Cumulative probability')
axes[0].yaxis.set_major_formatter(mtick.PercentFormatter(1,decimals=1))
axes[1].set_title('Eligible loans still at risk')
axes[1].set_ylabel('Loans before month-end events')
for ax in axes:
    ax.set_xlabel('Months after first observation')
    ax.set_xticks([1,6,12,18,24]); ax.set_xlim(1,24); ax.set_ylim(bottom=0)
    ax.grid(axis='y',alpha=.2); ax.legend(frameon=False,fontsize=9)
fig.savefig(figures/'incidence-and-risk.png',bbox_inches='tight')
plt.show()
'''),
md('''### 4. Same-age incidence with uncertainty
Each estimate uses its segment's own denominator. The intervals do not establish
a causal difference; the all-eligible cohort overlaps the two segments and is not additive.
'''),
code('''fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
for offset,(segment,(label,color,line)) in zip([-.35,0,.35],styles.items()):
    rows=[r for r in summary['horizons'] if r['segment']==segment]
    x=[r['observation_age']+offset for r in rows]
    y=[r['cif_d3'] for r in rows]
    assert all(r['ci_lower'] is not None and r['ci_upper'] is not None for r in rows), 'Keep unavailable intervals explicit'
    err=[[r['cif_d3']-r['ci_lower'] for r in rows],[r['ci_upper']-r['cif_d3'] for r in rows]]
    ax.errorbar(x,y,yerr=err,label=label,color=color,fmt='o',capsize=4,ms=5)
    for xx,r in zip(x,rows):
        if r['sparse_d3']:
            ax.annotate(f"Sparse: {r['observed_d3_count']} events",(xx,r['cif_d3']),
                        xytext=(18,22),textcoords='offset points',fontsize=9,
                        arrowprops={'arrowstyle':'-','color':'#525252'})
ax.set_title('2012 sample: 6 / 12 / 24-month first-D3 incidence')
ax.set_xlabel('Months after first observation (markers offset for legibility)')
ax.set_ylabel('Probability and 95% IID loan-bootstrap interval')
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1,decimals=1))
ax.set_xticks([6,12,24]); ax.set_ylim(bottom=0); ax.grid(axis='y',alpha=.2)
ax.legend(frameon=False)
fig.savefig(figures/'horizon-uncertainty.png',bbox_inches='tight')
plt.show()
'''),
md('''### 5. Stock is a different question
The following monthly stock uses all reported loans, including entry-ineligible
loans, and can count the same delinquent loan in several months. It must not be
interpreted as the cumulative first-event curve above.
'''),
code('''with duckdb.connect() as db:
    relation=db.read_parquet(str(run/'vintage_stock.parquet')).order('observation_age')
    names=relation.columns
    stock=relation.fetchall()
stock=[dict(zip(names,r)) for r in stock]
fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
ax.plot([r['observation_age'] for r in stock],[r['d3_stock_share'] for r in stock],color='#1f5b99',marker='.',lw=2)
ax.set_title('2012 sample: numeric-D3 share of usable active loan stock')
ax.set_xlabel('Months after first observation'); ax.set_ylabel('D3 loans / usable active loans')
ax.set_xticks([0,6,12,18,24]); ax.set_xlim(0,24); ax.set_ylim(bottom=0)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1,decimals=2)); ax.grid(axis='y',alpha=.2)
fig.savefig(figures/'stock-delinquency.png',bbox_inches='tight')
plt.show()
print('Private figure directory:',figures)
'''),
md('''## Takeaways
### Evidence-based next action
Keep Relief and non-Relief diagnostics separate before model development. The
sample's composition and selected refinance populations are alternative explanations
for the observed separation; this notebook does not identify a program effect.

Obtain the remaining authorized vintages before claiming cross-vintage performance
or selecting a model/underwriting strategy. Retain the exclusion share and at-risk
counts beside any future heatmap. The current curves do not establish approval
rates, profit improvements, causal uplift or production readiness.

Private source/run hashes and independent source-member checks are recorded above.
Do not upload the executed notebook or plots before the research-publication review.
''')]
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
             'language_info':{'name':'python','version':'3.12'}}
nbf.validate(nb)
nbf.write(nb,root/'notebooks/02_vintage.ipynb')
