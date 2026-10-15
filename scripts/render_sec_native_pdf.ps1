$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot;$out=Join-Path $root 'artifacts\private\sec-native-render-20261015'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$manifest=Get-Content (Join-Path $root 'artifacts\private\sec-workbook-scope-audit-1133f2bb3c7b\receipt.json') -Raw | ConvertFrom-Json
$app=$null;$book=$null;$owned=$false;$reads=[Collections.Generic.List[object]]::new()
try{
 $app=New-Object -ComObject Excel.Application;if($app.Workbooks.Count -ne 0){throw 'Nonempty Excel instance'}
 $owned=$true;$app.Visible=$false;$app.DisplayAlerts=$false;$app.EnableEvents=$false;$app.AutomationSecurity=3
 foreach($s in @($manifest.scopes | Where-Object {$_.query.years -eq '5' -and $_.query.interest_concept -eq 'InterestExpenseNonoperating'})){
  $source=Join-Path $root $s.workbook;$hash=(Get-FileHash -LiteralPath $source).Hash
  if($hash -ine $s.sha256){throw 'Source changed'}
  $book=$app.Workbooks.Open($source,0,$true)
  foreach($view in @(@('Analysis','A2:D15','summary'),@('Analysis','I18:N25','calculations'),@('Facts','A2:H13','facts'))){
   $sheet=$book.Worksheets.Item($view[0]);$setup=$sheet.PageSetup
   $setup.PrintArea=$view[1];$setup.Orientation=2;$setup.Zoom=$false;$setup.FitToPagesWide=1;$setup.FitToPagesTall=1
   $pdf=Join-Path $out ($s.query.cik+'-'+$view[2]+'.pdf');$sheet.ExportAsFixedFormat(0,$pdf)
   [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($setup);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet)
  }
  $analysis=$book.Worksheets.Item('Analysis');$facts=$book.Worksheets.Item('Facts')
  $cik=$analysis.Range('B4').Text;$exact=$facts.Range('E6').Text
  if($cik -cne $s.query.cik){throw 'CIK display changed'}
  $reads.Add([ordered]@{cik=$cik;exact_first_fact_text=$exact;source=$source;source_sha256=$hash})
  [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($analysis);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($facts)
  $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
  if((Get-FileHash -LiteralPath $source).Hash -ne $hash){throw 'Source was saved'}
 }
 [ordered]@{status='EXPORTED_NEEDS_VISUAL_REVIEW';reads=$reads;excel_version=$app.Version;sources_unchanged=$true} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $out 'receipt.json') -Encoding utf8
}finally{if($book){$book.Close($false)};if($app){if($owned){$app.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)};[GC]::Collect();[GC]::WaitForPendingFinalizers()}
