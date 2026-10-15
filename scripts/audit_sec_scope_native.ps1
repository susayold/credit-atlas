param([Parameter(Mandatory=$true)][string]$PlanPath,[string[]]$Sheets=@('Analysis','Facts'))
$ErrorActionPreference='Stop'
$plan=Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
$out=[IO.Path]::GetFullPath($plan.output_folder)
if(-not $out.StartsWith((Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts\private\native-excel-qa-sec-'),[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid native scope'}
$app=$null;$book=$null;$owned=$false;$results=[Collections.Generic.List[object]]::new()
try {
 $app=New-Object -ComObject Excel.Application
 if($app.Workbooks.Count -ne 0){throw 'Nonempty Excel instance'}
 $owned=$true;$app.Visible=$false;$app.DisplayAlerts=$false;$app.EnableEvents=$false;$app.AskToUpdateLinks=$false;$app.AutomationSecurity=3
 foreach($entry in $plan.books){
  $path=[IO.Path]::GetFullPath($entry.copy)
  if(-not $path.StartsWith($out+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Copy outside QA scope'}
  $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if($hash -ine $entry.source_sha256){throw 'Input bytes changed'}
  $book=$app.Workbooks.Open($path,0,$true);$app.CalculateFullRebuild()
  $failed=[Collections.Generic.List[object]]::new();$checked=0;$formulas=0
  foreach($sheetName in $Sheets){
   $sheet=$book.Worksheets.Item($sheetName);$range=$sheet.UsedRange
   $values=$range.Value2;$formulaValues=$range.Formula;$firstRow=$range.Row;$firstCol=$range.Column
   foreach($cell in @($entry.cells | Where-Object {$_.sheet -ceq $sheetName})){
    if($cell.cell -notmatch '^([A-Z]+)([0-9]+)$'){throw 'Invalid cell address'}
    $col=0;foreach($character in $Matches[1].ToCharArray()){$col=$col*26+([int]$character-[int][char]'A'+1)}
    $row=[int]$Matches[2];$r=$row-$firstRow+1;$c=$col-$firstCol+1
    $value=$values[$r,$c];$formula=$formulaValues[$r,$c];$passed=$true
    if($cell.kind -in @('n','d')){
     $expected=if($cell.kind -eq 'd'){
      if($cell.expected -is [DateTime]){$cell.expected.ToUniversalTime().ToOADate()}
      else{[DateTimeOffset]::Parse([string]$cell.expected,[Globalization.CultureInfo]::InvariantCulture).UtcDateTime.ToOADate()}
     }else{[double]::Parse([string]$cell.expected,[Globalization.CultureInfo]::InvariantCulture)}
     $passed=($value -is [double] -or $value -is [int]) -and [Math]::Abs([double]$value-$expected) -le [Math]::Max(1e-10,[Math]::Abs($expected)*1e-13)
    } else {$passed=[string]$value -ceq [string]$cell.expected}
    if($null -ne $cell.formula){
     $formulas++
     # Excel removes optional quoting around simple sheet names;references remain exact.
     $expectedFormula=('='+[string]$cell.formula) -creplace "'(Facts|Analysis|Maturities)'!",'$1!'
     $actualFormula=([string]$formula) -creplace "'(Facts|Analysis|Maturities)'!",'$1!'
     $passed=$passed -and ($actualFormula -ceq $expectedFormula)
    }
    $checked++
    if(-not $passed){$failed.Add([ordered]@{sheet=$sheetName;cell=$cell.cell;expected=$cell.expected;actual=$value;expected_formula=$cell.formula;actual_formula=$formula})}
   }
   [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($range);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet)
  }
  $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $hash){throw 'QA copy saved unexpectedly'}
  $results.Add([ordered]@{source=$entry.source;source_sha256=$hash;cells_checked=$checked;formulas_checked=$formulas;failures=$failed})
  Write-Output ('Native workbook '+$results.Count+' / '+$plan.books.Count+';failures '+$failed.Count)
 }
 $failures=@($results | ForEach-Object {$_.failures})
 [ordered]@{status=if($failures.Count -eq 0){'PASS'}else{'FAIL'};excel_version=$app.Version;books=$results;failed_checks=$failures.Count;copies_not_saved=$true} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $out 'receipt.json') -Encoding utf8
} finally {
 if($book){$book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)}
 if($app){if($owned){$app.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)}
 [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
