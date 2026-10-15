param([Parameter(Mandatory=$true)][string]$CasesPath)
$ErrorActionPreference='Stop'
$plan=Get-Content -LiteralPath $CasesPath -Raw | ConvertFrom-Json
$out=[IO.Path]::GetFullPath($plan.output_folder)
if(-not $out.StartsWith((Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts\private\native-excel-qa-'),[StringComparison]::OrdinalIgnoreCase)){throw 'Unexpected QA target'}
$app=$null;$book=$null;$owned=$false;$results=[Collections.Generic.List[object]]::new()
try {
 $app=New-Object -ComObject Excel.Application
 if($app.Workbooks.Count -ne 0){throw 'Nonempty Excel application'}
 $owned=$true;$app.Visible=$false;$app.DisplayAlerts=$false;$app.EnableEvents=$false;$app.AskToUpdateLinks=$false;$app.AutomationSecurity=3
 foreach($case in $plan.cases){
  $path=[IO.Path]::GetFullPath($case.copy)
  if(-not $path.StartsWith($out+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'QA copy escapes scope'}
  $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  $book=$app.Workbooks.Open($path,0,$true)
  foreach($change in $case.changes){
   $sheet=$book.Worksheets.Item($change.sheet);$range=$sheet.Range($change.cell)
   if($null -eq $change.value){$range.ClearContents() | Out-Null}
   elseif($change.value -is [string]){$range.Formula="'"+[string]$change.value}
   else{$range.Value2=[double]$change.value}
   [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($range);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet)
  }
  $app.CalculateFullRebuild();$reads=[Collections.Generic.List[object]]::new()
  foreach($expected in $case.expected){
   $sheet=$book.Worksheets.Item($expected.sheet);$range=$sheet.Range($expected.cell);$value=$range.Value2
   $passed=if($expected.value -is [string]){$value -ceq $expected.value}else{($value -is [double] -or $value -is [int]) -and [Math]::Abs([double]$value-[double]$expected.value) -le [Math]::Max(0.000000000001,[Math]::Abs([double]$expected.value)*0.00000000000001)}
   $reads.Add([ordered]@{sheet=$expected.sheet;cell=$expected.cell;expected=$expected.value;actual=$value;passed=$passed})
   [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($range);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet)
  }
  $results.Add([ordered]@{name=$case.name;reads=$reads;copy=$path;copy_sha256_before=$hash})
  $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $hash){throw 'Disposable input copy was saved unexpectedly'}
  Write-Output $case.name
 }
 $failed=@($results | ForEach-Object {$_.reads} | Where-Object {-not $_.passed})
 [ordered]@{status=if($failed.Count -eq 0){'PASS'}else{'FAIL'};excel_version=$app.Version;cases=$results;failed_checks=$failed.Count;copies_not_saved=$true;mutation_scope='Disposable read-only copies, memory only'} | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath (Join-Path $out 'perturbation-receipt.json') -Encoding utf8
} finally {
 if($book){$book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)}
 if($app){if($owned){$app.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)}
 [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
