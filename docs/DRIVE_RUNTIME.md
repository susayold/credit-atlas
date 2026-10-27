# Drive-backed D02 runtime

This first Drive-backed runtime is designed to serve the complete NSMO/D02 page in read-only
mode, including the separately scoped HUD FHA and FHFA NMDB context panels. It
reads source-bound aggregate receipts, dictionaries, curated benchmark files,
and D02 workbooks from the Credit Atlas Drive folder. It does not download them
to the checkout, create a disk cache, or persist review databases locally.
POST endpoints are disabled; the SQLite schemas needed by the existing server
live only in process memory. Only the page's explicit GET routes and four D02
workbook downloads are enabled. Other Atlas workspaces are not yet converted
to Drive-backed storage.

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

The FHFA geography ZIP uses offset/count range reads with a four-block
in-memory LRU (up to 4 MiB); it creates no local file or persistent cache.
D02 workbook responses are bounded to 100 MiB and assembled in memory.

The code path supports receipt-bound NSMO/D02 and its HUD/NMDB context reads
from Drive, with no local persistent app state. Live Drive startup and the
complete page still require the one-time OAuth configuration above and an
end-to-end acceptance run; source inspection alone is not acceptance evidence.
This does not yet move D01, HAMP, Bondora, Excel exports, or other workspaces to
Drive-backed storage, and does not count as completion of the project-wide
storage requirement.
