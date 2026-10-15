# Migration boundary

| Existing item | Action | Why |
|---|---|---|
| Prosper raw data and artifacts | Keep unchanged | Distinct population |
| Existing website and Excel | Keep unchanged | New release not ready |
| Existing Python environment | Read versions only | New isolated environment |
| Status/target/economics code | Do not copy | Source semantics differ |
| Test/config/export patterns | Reimplement only where needed | Avoid inherited assumptions |
| New mortgage raw/source documents | Private paths in new repo | Separate provenance and rights |

No operation in the first V4 implementation is intended to alter the old project.

