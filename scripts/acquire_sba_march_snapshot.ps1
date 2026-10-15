$ErrorActionPreference='Stop'
$taskRoot='D:\data\Codex\credit-atlas'
if((Get-PSDrive -Name D).Free -lt 3GB){throw 'Need at least 3GB free for private raw archive and profiling'}
$taskOut=Join-Path $taskRoot ('data\private\business-archive\sba-march-candidate-'+[guid]::NewGuid().ToString('N').Substring(0,12))
New-Item -ItemType Directory -Path $taskOut | Out-Null
$taskNames=@('FOIA_504_FY1991_FY2009_asof_260331.csv','FOIA_504_FY2010_Present_asof_260331.csv','FOIA_7a_FY1991_FY1999_asof_260331.csv','FOIA_7a_FY2000_FY2009_asof_260331.csv','FOIA_7a_FY2010_FY2019_asof_260331.csv','FOIA_7a_FY2020_Present_asof_260331.csv')
$taskFiles=@()
foreach($taskName in $taskNames){
 $taskUrl='https://data.sba.gov/sites/default/files/uploaded_resources/'+$taskName
 $taskFile=Join-Path $taskOut $taskName
 $taskMetadata=& curl.exe --fail --location --silent --show-error --max-time 180 --max-filesize 536870912 --output $taskFile --write-out '%{json}' $taskUrl
 if($LASTEXITCODE -ne 0){@{status='PARTIAL_DOWNLOAD_FAILED';files=$taskFiles;failed_url=$taskUrl;curl_exit_code=$LASTEXITCODE;candidate_snapshot_date='2026-03-31';actual_snapshot_dates_verified=$false} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'receipt.json') -Encoding utf8;throw 'SBA candidate archive download failed;successful raw files retained'}
 $taskMeta=$taskMetadata | ConvertFrom-Json
 $taskFiles+=@{file=$taskName;requested_url=$taskUrl;resolved_url=$taskMeta.url_effective;http_status=$taskMeta.http_code;bytes=(Get-Item -LiteralPath $taskFile).Length;sha256=(Get-FileHash -LiteralPath $taskFile -Algorithm SHA256).Hash.ToLower();retrieved_at=[DateTimeOffset]::UtcNow.ToString('o');url_basis='Historical filename advertised on SBA legacy catalog;modern public download naming convention;HTTP presence checked,contents require profiling'}
 @{status='ACQUISITION_IN_PROGRESS';files=$taskFiles;candidate_snapshot_date='2026-03-31';actual_snapshot_dates_verified=$false} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'receipt.json') -Encoding utf8
 Write-Output ($taskName+' · downloaded '+$taskFiles[-1].bytes+' bytes')
}
@{status='RAW_ACQUIRED_NEEDS_PROFILE';files=$taskFiles;candidate_snapshot_date='2026-03-31';actual_snapshot_dates_verified=$false;publication_time_qualified=$false;source_role='Separate candidate historical snapshot,not added to frozen business case';script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower()} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'receipt.json') -Encoding utf8
Write-Output ('ARCHIVE_OUTPUT '+$taskOut)
