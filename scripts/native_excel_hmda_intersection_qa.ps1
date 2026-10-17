param(
    [Parameter(Mandatory = $true)]
    [string]$WorkbookPath,
    [string]$ReceiptPath
)

$ErrorActionPreference = 'Stop'
$resolvedWorkbook = (Resolve-Path -LiteralPath $WorkbookPath).Path
$beforeHash = (Get-FileHash -LiteralPath $resolvedWorkbook -Algorithm SHA256).Hash.ToLowerInvariant()
$excel = $null
$workbook = $null
$receipt = [ordered]@{
    status = 'FAIL'
    workbook_path = $resolvedWorkbook
    workbook_sha256_before = $beforeHash
    excel_version = $null
    read_only = $true
    macros_disabled = $true
    external_links = $null
    formula_count = $null
    reconciliation_checks = @()
    formula_errors = @()
    workbook_bytes_unchanged = $false
    verified_at = (Get-Date).ToUniversalTime().ToString('o')
}

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.EnableEvents = $false
    $excel.AskToUpdateLinks = $false
    $excel.AutomationSecurity = 3 # msoAutomationSecurityForceDisable
    $receipt.excel_version = [string]$excel.Version

    # UpdateLinks=0, ReadOnly=true, IgnoreReadOnlyRecommended=true.
    $workbook = $excel.Workbooks.Open($resolvedWorkbook, 0, $true, [Type]::Missing,
        [Type]::Missing, [Type]::Missing, $true)
    $sheetNames = @($workbook.Worksheets | ForEach-Object { [string]$_.Name })
    if (($sheetNames -join '|') -ne 'Summary|Actions|Method & sources') {
        throw "Unexpected worksheet set: $($sheetNames -join ', ')"
    }

    $excel.CalculateFullRebuild()
    $formulaCount = 0
    $formulaErrors = [System.Collections.Generic.List[string]]::new()
    foreach ($sheet in $workbook.Worksheets) {
        $used = $sheet.UsedRange
        for ($row = 1; $row -le $used.Rows.Count; $row++) {
            for ($column = 1; $column -le $used.Columns.Count; $column++) {
                $cell = $used.Cells.Item($row, $column)
                if ($cell.HasFormula) { $formulaCount++ }
                $shown = [string]$cell.Text
                if ($shown -in @('#REF!', '#VALUE!', '#DIV/0!', '#NAME?', '#NUM!', '#N/A', '#NULL!')) {
                    $formulaErrors.Add("$($sheet.Name)!$($cell.Address())=$shown")
                }
            }
        }
    }
    $checks = @()
    foreach ($row in 19..22) {
        $checks += [ordered]@{
            cell = "Summary!B$row"
            label = [string]$workbook.Worksheets.Item('Summary').Cells.Item($row, 1).Value2
            result = [string]$workbook.Worksheets.Item('Summary').Cells.Item($row, 2).Value2
        }
    }
    $linkSources = $workbook.LinkSources(1)
    $externalLinkCount = if ($null -eq $linkSources) { 0 } else { @($linkSources).Count }
    $receipt.external_links = $externalLinkCount
    $receipt.formula_count = $formulaCount
    $receipt.reconciliation_checks = $checks
    $receipt.formula_errors = @($formulaErrors)

    if ($formulaCount -ne 12) { throw "Expected 12 formulas, found $formulaCount" }
    if ($externalLinkCount -ne 0) { throw "Expected no external links, found $externalLinkCount" }
    if ($formulaErrors.Count -ne 0) { throw "Excel reported formula errors" }
    if (@($checks | Where-Object { $_.result -notin @('PASS', 'N/A') }).Count -ne 0) {
        throw 'One or more workbook reconciliation checks did not pass'
    }

    $workbook.Close($false)
    $workbook = $null
    $excel.Quit()
    $excel = $null
    $afterHash = (Get-FileHash -LiteralPath $resolvedWorkbook -Algorithm SHA256).Hash.ToLowerInvariant()
    $receipt.workbook_sha256_after = $afterHash
    $receipt.workbook_bytes_unchanged = $beforeHash -eq $afterHash
    if (-not $receipt.workbook_bytes_unchanged) { throw 'Read-only Excel QA changed workbook bytes' }
    $receipt.status = 'PASS'
}
catch {
    $receipt.error = $_.Exception.Message
    throw
}
finally {
    if ($null -ne $workbook) { $workbook.Close($false) }
    if ($null -ne $excel) { $excel.Quit() }
    if ($null -ne $ReceiptPath) {
        $resolvedReceipt = [System.IO.Path]::GetFullPath($ReceiptPath)
        $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resolvedReceipt -Encoding utf8
    }
}

$receipt | ConvertTo-Json -Depth 8
