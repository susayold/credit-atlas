"""Source-filter-only principal maturity workbook export."""
from .sec_debt import report as maturity_report
from .sec_workbook import _export_document


def document(views,query):
    if not isinstance(query,dict) or 'view_id' not in query or set(query)-{'view_id','cik','accession','asof','debt_scope'}:
        raise ValueError('Maturity workbook accepts source filters only')
    if any(not isinstance(v,str) or len(v)>64 for v in query.values()):raise ValueError('Bounded string source filters required')
    report=maturity_report(views,query['view_id'],query)
    if not report['statement']:raise ValueError('Selected annual filing required for maturity export')
    return report


def export_workbook(service,query):
    return _export_document(service,document(service.sec_views,query),'build_sec_debt_workbook.mjs','CreditAtlas-Maturities.xlsx','sec-debt-workbook-')
