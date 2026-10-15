$ErrorActionPreference='Stop'
$taskRoot='D:\data\Codex\credit-atlas'
$taskOut=Join-Path $taskRoot ('data\private\retail-reference\uci350-reference-'+[guid]::NewGuid().ToString('N').Substring(0,12))
New-Item -ItemType Directory -Path $taskOut | Out-Null
$taskSources=@(@{file='metadata.json';url='https://archive.ics.uci.edu/api/dataset?id=350'},@{file='dataset-page.html';url='https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients'})
$taskFiles=@()
foreach($taskSource in $taskSources){
 $taskFile=Join-Path $taskOut $taskSource.file
 $taskResult=& curl.exe --fail --location --silent --show-error --max-time 45 --max-filesize 5242880 --output $taskFile --write-out '%{json}' $taskSource.url
 if($LASTEXITCODE -ne 0){@{status='DOWNLOAD_FAILED';failed_url=$taskSource.url;curl_exit_code=$LASTEXITCODE;successful_files=$taskFiles;client_rows_downloaded=0} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'failed.json') -Encoding utf8;throw 'UCI reference download failed'}
 $taskMeta=$taskResult | ConvertFrom-Json
 $taskFiles+=@{file=$taskSource.file;requested_url=$taskSource.url;resolved_url=$taskMeta.url_effective;http_status=$taskMeta.http_code;bytes=(Get-Item -LiteralPath $taskFile).Length;sha256=(Get-FileHash -LiteralPath $taskFile -Algorithm SHA256).Hash.ToLower();retrieved_at=[DateTimeOffset]::UtcNow.ToString('o')}
}
$taskMetadata=Get-Content -LiteralPath (Join-Path $taskOut 'metadata.json') -Raw | ConvertFrom-Json
if($taskMetadata.data.uci_id -ne 350 -or $taskMetadata.data.num_instances -ne 30000){throw 'UCI metadata scope changed'}
@{status='ACQUIRED';files=$taskFiles;source_role='current_publisher_metadata_and_dictionary_reference';client_rows_downloaded=0;added_temporal_cohorts=0;script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower()} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'receipt.json') -Encoding utf8
@{output=$taskOut;files=$taskFiles.Count;client_rows_downloaded=0;added_temporal_cohorts=0} | ConvertTo-Json -Compress
