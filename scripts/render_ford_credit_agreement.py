import pypdfium2 as pdfium
from pathlib import Path
folder=Path('data/private/sec-documents/sec-documents-6f8e86a15804');pdf=pdfium.PdfDocument(folder/'ford-term-loan-20250728.pdf')
for i in [0,9,41]:pdf[i].render(scale=1.3).to_pil().save(folder/('page-'+str(i+1)+'.png'))
