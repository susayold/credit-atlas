# Drive-backed D02 runtime

This first Drive-backed runtime serves the NSMO/D02 pages in read-only mode. It
streams the source-bound aggregate receipts and public dictionaries from the
Credit Atlas Drive folder. It does not download them to the checkout, create a
disk cache, or persist review databases locally. POST endpoints are disabled;
the SQLite schemas needed by the existing server live only in process memory.
Other Atlas workspaces are not yet converted to Drive-backed storage.

## One-time rclone setup

Install rclone and create a Drive remote named `creditatlas` in:

`D:\data\CodexState\config\creditatlas-rclone.conf`

Configure the remote with exactly:

- backend: Google Drive (`drive`)
- OAuth scope: `drive.readonly` (metadata and file contents; no upload, rename,
  or delete permission)
- root folder ID: `1YCHLG7p7AMCF8hpWOvP4_iYzpqQ92h7H` (the verified Credit Atlas
  Drive root)

Sign in to the Google account that owns or can read the Credit Atlas folder and
complete Google's consent screen. The OAuth scope is account-wide read-only, so
the token can read other files available to that Google account. The remote
root folder and application path checks keep this runtime operating on the
Credit Atlas project tree, but do not narrow the OAuth grant. Keep the rclone config outside
the repository and Drive project folders. Do not paste its token into chat or
commit/upload the config.

The prior `drive.metadata.readonly` grant cannot read file bytes, so it cannot
serve this application. This runtime verifies the rclone config's exact scope
and root-folder ID before it starts.

## Start

From the clean code checkout on D:, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_nsmo_drive.ps1
```

Open `http://127.0.0.1:8770/nsmo`. The app code/static files run from the D:
checkout. Data reads use `rclone lsjson` for metadata and `rclone cat` for
content, streaming over process pipes; neither command writes source bytes to a
local data file. Do not add `rclone copy`, `sync`, or a cache-enabled mount to
this read-only runtime. Rclone may refresh its OAuth token in the configuration
file under `D:\data\CodexState`.

## Acceptance boundary

The code supports receipt-bound NSMO/D02 reads from Drive and no local
persistent app state. Live Drive startup still requires the one-time OAuth
configuration above. This does not yet move D01, HAMP, Bondora, Excel exports,
or other workspaces to Drive-backed storage, and does not count as completion
of the project-wide storage requirement.
