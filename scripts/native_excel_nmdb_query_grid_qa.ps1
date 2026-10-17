param(
    [Parameter(Mandatory=$true)][string]$NewWorkbook,
    [Parameter(Mandatory=$true)][string]$OutstandingWorkbook,
    [Parameter(Mandatory=$true)][string]$ReceiptPath
)

$ErrorActionPreference='Stop'
$items=@(
    @{path=(Resolve-Path -LiteralPath $NewWorkbook).Path;product='new_annual';expected_rows=27;expected_suppressed=7},
    @{path=(Resolve-Path -LiteralPath $OutstandingWorkbook).Path;product='outstanding_quarterly';expected_rows=54;expected_suppressed=0}
)
$resolvedReceipt=[IO.Path]::GetFullPath($ReceiptPath)
foreach($item in $items){if(-not $item.path.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){throw 'NMDB workbook inputs must remain on D:'}}
if(-not $resolvedReceipt.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){throw 'Native Excel receipt must remain on D:'}

$checks=[Collections.Generic.List[object]]::new()
$excel=$null;$owned=$false;$book=$null
try {
    $excel=New-Object -ComObject Excel.Application
    if($excel.Workbooks.Count -ne 0){throw 'Fresh Excel application unexpectedly has workbooks; refusing to change application settings'}
    $owned=$true
    $excel.Visible=$false;$excel.DisplayAlerts=$false;$excel.AskToUpdateLinks=$false;$excel.EnableEvents=$false;$excel.AutomationSecurity=3
    $version=[string]$excel.Version
    if(-not $version.StartsWith('16.')){throw "Expected Microsoft Excel 16.x, found $version"}

    foreach($item in $items){
        $path=$item.path
        $before=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        $book=$excel.Workbooks.Open($path,0,$true,[Type]::Missing,[Type]::Missing,[Type]::Missing,$true)
        if(-not $book.ReadOnly){throw 'NMDB query workbook did not open read-only'}
        $sheetNames=@($book.Worksheets | ForEach-Object {[string]$_.Name})
        if(($sheetNames -join '|') -ne 'Start Here|Selected data|Definitions|Quality & lineage'){
            throw "Unexpected workbook sheets: $($sheetNames -join ', ')"
        }
        $start=$book.Worksheets.Item('Start Here')
        $data=$book.Worksheets.Item('Selected data')
        if([string]$start.Range('B2').Value2 -notmatch [regex]::Escape($item.product.Split('_')[0])){throw 'Excel product label differs from the requested query'}

        $excel.CalculateFullRebuild()
        $deadline=[DateTime]::UtcNow.AddSeconds(60)
        while($excel.CalculationState -ne 0){if([DateTime]::UtcNow -gt $deadline){throw 'Excel calculation did not finish'};Start-Sleep -Milliseconds 100}

        if($data.ListObjects.Count -ne 1){throw 'Expected one filtered Excel Table in Selected data'}
        $table=$data.ListObjects.Item(1)
        if($table.Name -ne 'NMDBSelectedData' -or $table.ListColumns.Count -ne 18){throw 'Selected-data Table shape differs from the 18-column export contract'}
        $rows=[int]$table.DataBodyRange.Rows.Count
        if($rows -ne $item.expected_rows){throw "Expected $($item.expected_rows) selected observations, found $rows"}
        if(-not $table.ShowAutoFilter){throw 'Excel Table filter is not enabled'}
        if($data.ChartObjects().Count -ne 1){throw 'Expected one filtered-series chart in the selected-data sheet'}

        $suppressed=0;$formulaCount=0;$formulaErrors=[Collections.Generic.List[string]]::new()
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
        for($r=2;$r -le $table.DataBodyRange.Rows.Count+1;$r++){
            if([string]$data.Cells.Item($r,16).Value2 -like 'Yes*'){
                $suppressed++
                if($null -ne $data.Cells.Item($r,13).Value2 -and [string]$data.Cells.Item($r,13).Value2 -ne ''){
                    throw 'A source-suppressed selected value was shown as numeric in Excel'
                }
            }
        }
        if($suppressed -ne $item.expected_suppressed){throw "Expected $($item.expected_suppressed) suppressed rows, found $suppressed"}
        if($formulaCount -ne 0 -or $formulaErrors.Count -ne 0){throw 'Query export should contain no formulas or Excel formula errors'}
        $links=$book.LinkSources(1)
        $linkCount=if($null -eq $links){0}else{@($links).Count}
        if($linkCount -ne 0){throw 'Filtered NMDB workbook has external links'}

        $checks.Add([ordered]@{
            file=[IO.Path]::GetFileName($path);product=$item.product;read_only=[bool]$book.ReadOnly
            selected_rows=$rows;selected_data_columns=[int]$table.ListColumns.Count;table_filter_visible=[bool]$table.ShowAutoFilter
            charts=[int]$data.ChartObjects().Count;suppressed_rows=$suppressed;formula_cells=$formulaCount
            formula_errors=@($formulaErrors);external_links=$linkCount;sha256_before=$before
        })
        $book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book);$book=$null
        if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $before){throw 'Read-only Excel recalc changed workbook bytes'}
        $checks[$checks.Count-1]['sha256_after']=$before
        $checks[$checks.Count-1]['bytes_unchanged']=$true
        Write-Output ('Excel 16.0 read/recalc pass: '+[IO.Path]::GetFileName($path))
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($table)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($data)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($start)
    }
    $receipt=[ordered]@{
        evidence_type='nmdb_market_statistics_native_excel_query_grid_acceptance';status='PASS'
        verified_at_utc=[DateTime]::UtcNow.ToString('o');excel_version=$version;read_only=$true
        macros_disabled=$true;external_links_updated=$false;full_rebuild=$true;workbooks=$checks
        limitation='Native Excel verification covers two representative exports. API and all 18 XLSX columns were separately compared across the 56-query filtered-workbook grid.'
    }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($resolvedReceipt))|Out-Null
    [IO.File]::WriteAllText($resolvedReceipt,($receipt|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
    $receipt|ConvertTo-Json -Depth 10
} finally {
    if($book){$book.Close($false);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)}
    if($excel){if($owned){$excel.Quit()};[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)}
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
