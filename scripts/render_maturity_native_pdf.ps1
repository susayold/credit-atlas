$ErrorActionPreference='Stop';$root='D:\data\Codex\credit-atlas';$out=Join-Path $root 'artifacts\private\maturity-native-render-20261015'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$m=Get-Content (Join-Path $root 'artifacts\private\maturity-workbook-scope-audit-46d6a12f8d2d\receipt.json') -Raw | ConvertFrom-Json
$app=$null;$book=$null;$owned=$false;$results=[Collections.Generic.List[object]]::new()
try{
 $app=New-Object -ComObject Excel.Application;if($app.Workbooks.Count -ne 0){throw 'Nonempty Excel instance'}
 $owned=$true;$app.Visible=$false;$app.DisplayAlerts=$false;$app.EnableEvents=$false;$app.AutomationSecurity=3
 foreach($s in $m.scopes){
  $path=Join-Path $root $s.workbook;$hash=(Get-FileHash -LiteralPath $path).Hash;if($hash -ine $s.sha256){throw 'Source changed'}
  $book=$app.Workbooks.Open($path,0,$true)
  foreach($view in @(@('Maturities','A2:D24','summary'),@('Facts','A2:H11','facts'))){
   $sheet=$book.Worksheets.Item($view[0]);$setup=$sheet.PageSetup;$setup.PrintArea=$view[1];$setup.Orientation=2;$setup.Zoom=$false;$setup.FitToPagesWide=1;$setup.FitToPagesTall=1
   $name=$s.query.cik+'-'+$s.query.debt_scope+'-'+$view[2]+'.pdf';$sheet.ExportAsFixedFormat(0,(Join-Path $out $name))
   [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($setup);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet)
  }
  $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
  if((Get-FileHash -LiteralPath $path).Hash -ne $hash){throw 'Source saved'}
  $results.Add([ordered]@{source=$path;source_sha256=$hash;cik=$s.query.cik;family=$s.query.debt_scope})
 }
 [ordered]@{status='EXPORTED_NEEDS_VISUAL_REVIEW';books=$results;excel_version=$app.Version;sources_unchanged=$true}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $out 'receipt.json') -Encoding utf8
}finally{if($book){$book.Close($false)};if($app){if($owned){$app.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)};[GC]::Collect();[GC]::WaitForPendingFinalizers()}
