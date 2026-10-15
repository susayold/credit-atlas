param([Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference='Stop'
$plan=Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
$out=[IO.Path]::GetFullPath($plan.output_folder)
if(-not $out.StartsWith((Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts\private\native-excel-qa-'),[StringComparison]::OrdinalIgnoreCase)){throw 'Unexpected native QA target'}
$results=[Collections.Generic.List[object]]::new()
$app=$null;$owned=$false;$book=$null
try {
    $app=New-Object -ComObject Excel.Application
    if($app.Workbooks.Count -ne 0){throw 'Fresh Excel application unexpectedly has workbooks; refusing to change application settings'}
    $owned=$true
    $app.Visible=$false;$app.DisplayAlerts=$false;$app.AskToUpdateLinks=$false;$app.EnableEvents=$false;$app.AutomationSecurity=3
    $version=$app.Version;$build=$app.Build
    foreach($inputBook in $plan.books){
        $copy=[IO.Path]::GetFullPath($inputBook.copy)
        if(-not $copy.StartsWith($out+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Workbook copy escapes QA folder'}
        if((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash.ToLower() -ne $inputBook.source_sha256){throw 'Copy differs before Excel open'}
        $book=$app.Workbooks.Open($copy,0,$true)
        if(-not $book.ReadOnly){throw 'Expected read-only source copy'}
        $app.CalculateFullRebuild()
        $deadline=[DateTime]::UtcNow.AddSeconds(60)
        while($app.CalculationState -ne 0){if([DateTime]::UtcNow -gt $deadline){throw 'Native calculation did not finish'};Start-Sleep -Milliseconds 100}
        $values=[Collections.Generic.List[object]]::new()
        foreach($item in $inputBook.cells){
            $sheet=$book.Worksheets.Item($item.sheet);$cell=$sheet.Range($item.cell)
            $value=$cell.Value2
            $values.Add([ordered]@{sheet=$item.sheet;cell=$item.cell;value=$value;has_formula=[bool]$cell.HasFormula;formula=if($cell.HasFormula){[string]$cell.Formula}else{$null};text=[string]$cell.Text})
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($cell)
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet)
        }
        $results.Add([ordered]@{source=$inputBook.source;copy=$copy;read_only=$book.ReadOnly;values=$values})
        $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
        if((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash.ToLower() -ne $inputBook.source_sha256){throw 'Source copy unexpectedly saved'}
        if((Get-FileHash -LiteralPath $inputBook.source -Algorithm SHA256).Hash.ToLower() -ne $inputBook.source_sha256){throw 'Original source workbook changed'}
        Write-Output ('Native calculation read: '+[IO.Path]::GetFileName($copy))
    }
    [ordered]@{status='NATIVE_CALCULATION_OBSERVED';excel_version=$version;excel_build=$build;books=$results;originals_unchanged=$true;copies_not_saved=$true} | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath (Join-Path $out 'native-results.json') -Encoding utf8
} catch {
    [ordered]@{status='FAIL';reason=$_.Exception.Message;books_completed=$results.Count} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native-failed.json') -Encoding utf8
    throw
} finally {
    if($book){$book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)}
    if($app){if($owned){$app.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)}
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
