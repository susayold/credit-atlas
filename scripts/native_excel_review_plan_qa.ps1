param(
    [Parameter(Mandatory=$true)][string]$WorkbookPath,
    [Parameter(Mandatory=$true)][string]$ReceiptPath
)

$ErrorActionPreference='Stop'
$path=(Resolve-Path -LiteralPath $WorkbookPath).Path
$receiptPath=[IO.Path]::GetFullPath($ReceiptPath)
if(-not $path.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){throw 'Plan workbook must remain on D:'}
if(-not $receiptPath.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){throw 'Plan workbook receipt must remain on D:'}
$before=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
$excel=$null;$book=$null;$owned=$false
try {
    $excel=New-Object -ComObject Excel.Application
    if($excel.Workbooks.Count -ne 0){throw 'Fresh Excel application unexpectedly has workbooks; refusing to change application settings'}
    $owned=$true
    $excel.Visible=$false;$excel.DisplayAlerts=$false;$excel.AskToUpdateLinks=$false;$excel.EnableEvents=$false;$excel.AutomationSecurity=3
    $version=[string]$excel.Version
    if(-not $version.StartsWith('16.')){throw "Expected Microsoft Excel 16.x, found $version"}
    $book=$excel.Workbooks.Open($path,0,$true,[Type]::Missing,[Type]::Missing,[Type]::Missing,$true)
    if(-not $book.ReadOnly){throw 'Plan workbook did not open read-only'}
    $names=@($book.Worksheets|ForEach-Object{[string]$_.Name})
    if(($names -join '|') -ne 'Ke hoach|50 yeu cau|Du lieu|Phuong phap'){throw "Unexpected plan workbook sheets: $($names -join ', ')"}
    $excel.CalculateFullRebuild()
    $deadline=[DateTime]::UtcNow.AddSeconds(60)
    while($excel.CalculationState -ne 0){if([DateTime]::UtcNow -gt $deadline){throw 'Plan workbook recalculation did not finish'};Start-Sleep -Milliseconds 100}
    $formulaCount=0;$formulaErrors=[Collections.Generic.List[string]]::new()
    foreach($sheet in $book.Worksheets){
        $used=$sheet.UsedRange
        for($r=1;$r -le $used.Rows.Count;$r++){
            for($c=1;$c -le $used.Columns.Count;$c++){
                $cell=$used.Cells.Item($r,$c)
                if($cell.HasFormula){$formulaCount++}
                $shown=[string]$cell.Text
                if($shown -in @('#REF!','#VALUE!','#DIV/0!','#NAME?','#NUM!','#N/A','#NULL!','#SPILL!','#CALC!')){
                    $formulaErrors.Add("$($sheet.Name)!$($cell.Address())=$shown")
                }
            }
        }
    }
    if($formulaCount -ne 18){throw "Expected 18 plan formulas, found $formulaCount"}
    if($formulaErrors.Count -ne 0){throw 'Excel reported plan formula errors'}
    $plan=$book.Worksheets.Item('Ke hoach')
    $achieved=[double]$plan.Range('B11').Value2
    $total=[double]$plan.Range('C11').Value2
    $ratio=[double]$plan.Range('D11').Value2
    if($achieved -ne 26 -or $total -ne 50 -or [Math]::Abs($ratio-0.52) -gt 0.0000001){throw 'Plan ledger did not recalculate to 26/50'}
    if([string]$plan.Range('F22').Value2 -ne 'Đang làm' -or [string]$plan.Range('F23').Value2 -ne 'Đang làm'){
        throw 'N05/N06 task status unexpectedly changed'
    }
    if([string]$plan.Range('G22').Value2 -notmatch '235 scopes' -or [string]$plan.Range('G23').Value2 -notmatch '31,644 cells match API'){
        throw 'Excel does not show the latest N05/N06 query-grid evidence'
    }
    $n05Status=[string]$plan.Range('F22').Value2
    $n06Status=[string]$plan.Range('F23').Value2
    $links=$book.LinkSources(1)
    $externalLinks=if($null -eq $links){0}else{@($links).Count}
    if($externalLinks -ne 0){throw 'Plan workbook has external links'}
    $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
    if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $before){throw 'Read-only Excel recalculation changed plan workbook bytes'}
    $receipt=[ordered]@{
        evidence_type='native_excel_project_review_plan_workbook_acceptance';status='PASS'
        verified_at_utc=[DateTime]::UtcNow.ToString('o');file=[IO.Path]::GetFileName($path)
        excel_version=$version;read_only=$true;macros_disabled=$true;external_links_updated=$false
        sheets=$names;formula_cells=$formulaCount;formula_errors=@($formulaErrors);external_links=$externalLinks
        n05_n06_status=@($n05Status,$n06Status)
        ledger=@{achieved=$achieved;total=$total;ratio=$ratio}
        workbook_sha256_before=$before;workbook_sha256_after=$before;workbook_bytes_unchanged=$true
    }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($receiptPath))|Out-Null
    [IO.File]::WriteAllText($receiptPath,($receipt|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    $receipt|ConvertTo-Json -Depth 8
} finally {
    if($book){$book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)}
    if($excel){if($owned){$excel.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)}
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
