param([Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference='Stop';$plan=Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
$out=[IO.Path]::GetFullPath($plan.output_folder)
if(-not $out.StartsWith('D:\data\Codex\credit-atlas\artifacts\private\native-excel-qa-sec-perturb-',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid QA scope'}
$app=$null;$book=$null;$owned=$false;$results=[Collections.Generic.List[object]]::new()
try{
 $app=New-Object -ComObject Excel.Application;if($app.Workbooks.Count -ne 0){throw 'Nonempty Excel instance'}
 $owned=$true;$app.Visible=$false;$app.DisplayAlerts=$false;$app.EnableEvents=$false;$app.AutomationSecurity=3;$app.AskToUpdateLinks=$false
 foreach($b in $plan.books){
  $path=[IO.Path]::GetFullPath($b.copy);if(-not $path.StartsWith($out+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Copy outside QA scope'}
  if((Get-FileHash -LiteralPath $path).Hash -ine $b.sha256){throw 'Copy changed'}
  $book=$app.Workbooks.Open($path,0,$true);$facts=$book.Worksheets.Item('Facts');$analysis=$book.Worksheets.Item('Analysis')
  $num=$facts.Range($b.numerator_cell);$den=$facts.Range($b.denominator_cell);$originalNum=$num.Value2;$originalDen=$den.Value2
  foreach($case in $b.cases){
   $num.Value2=$originalNum;$den.Value2=$originalDen;$target=if($case.target -eq 'numerator'){$num}else{$den}
   if($null -eq $case.value){$target.ClearContents() | Out-Null}elseif($case.value -is [string]){$target.Formula="'"+$case.value}else{$target.Value2=[double]$case.value}
   $app.CalculateFullRebuild();$passed=$true;$actual=[Collections.Generic.List[object]]::new()
   foreach($address in @($b.output_cell,$b.summary_cell)){
    $range=$analysis.Range($address);$value=$range.Value2
    $ok=if($case.expected -is [string]){$value -ceq $case.expected}else{($value -is [double]) -and [Math]::Abs([double]$value-[double]$case.expected) -le 1e-12}
    $passed=$passed -and $ok;$actual.Add([ordered]@{cell=$address;value=$value;passed=$ok});[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($range)
   }
   $results.Add([ordered]@{source=$b.source;case=$case.name;expected=$case.expected;reads=$actual;passed=$passed})
  }
  [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($num);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($den)
  [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($facts);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($analysis)
  $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
  if((Get-FileHash -LiteralPath $path).Hash -ine $b.sha256){throw 'Copy saved unexpectedly'}
  Write-Output ('Cases checked '+$results.Count)
 }
 $failed=@($results | Where-Object {-not $_.passed})
 [ordered]@{status=if($failed.Count -eq 0){'PASS'}else{'FAIL'};cases=$results;failed_cases=$failed.Count;excel_version=$app.Version;copies_not_saved=$true} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $out 'receipt.json') -Encoding utf8
}finally{if($book){$book.Close($false)};if($app){if($owned){$app.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)};[GC]::Collect();[GC]::WaitForPendingFinalizers()}
