$ErrorActionPreference='Stop'
$taskRoot='D:\data\Codex\credit-atlas'
$taskOut=Join-Path $taskRoot ('data\private\mortgage\freddie-public-reference-'+[guid]::NewGuid().ToString('N').Substring(0,12))
New-Item -ItemType Directory -Path $taskOut | Out-Null
$taskSources=@(
 @{file='general-user-guide.pdf';url='https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf'},
 @{file='clarity-download-announcement.html';url='https://capitalmarkets.freddiemac.com/clarity/whats-new/december-2025-clarity-updates'},
 @{file='legacy-download-migration.html';url='https://freddiemac.embs.com/FLoan/menu.php'}
)
$taskFiles=@()
foreach ($taskSource in $taskSources) {
 $taskFile=Join-Path $taskOut $taskSource.file
 $taskMetadata= & curl.exe --fail --location --silent --show-error --max-time 45 --max-filesize 5242880 --output $taskFile --write-out '%{json}' $taskSource.url
 if ($LASTEXITCODE -ne 0) {
  @{status='DOWNLOAD_FAILED';url=$taskSource.url;curl_exit_code=$LASTEXITCODE;successful_files=$taskFiles;added_annual_vintages=0} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'failed.json') -Encoding utf8
  throw 'Public reference download failed'
 }
 $taskMeta=$taskMetadata | ConvertFrom-Json
 $taskItem=Get-Item -LiteralPath $taskFile
 if ($taskItem.Length -gt 5242880) {throw 'Reference size limit exceeded'}
 $taskFiles+=@{file=$taskSource.file;requested_url=$taskSource.url;resolved_url=$taskMeta.url_effective;http_status=$taskMeta.http_code;content_type=$taskMeta.content_type;bytes=$taskItem.Length;sha256=(Get-FileHash -LiteralPath $taskFile -Algorithm SHA256).Hash.ToLower();retrieved_at=[DateTimeOffset]::UtcNow.ToString('o');publisher_publication_at=$null}
}
@{status='ACQUIRED';source_role='public_reference_not_annual_loan_dataset';files=$taskFiles;added_annual_vintages=0;publisher_release_authenticated_for_supplied_zip=$false;script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower()} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskOut 'receipt.json') -Encoding utf8
@{output=$taskOut;files=$taskFiles.Count;added_annual_vintages=0} | ConvertTo-Json -Compress
