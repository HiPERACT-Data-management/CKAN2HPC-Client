# Module Reference

Complete documentation of every class and function in CKAN2HPC Client.

---

## config.py

### `class Config`

Reads `settings.ini` from the same directory as the module file and exposes configuration values as typed instance attributes.

**Raises:** `Exception` with the message `"settings.ini does not exist"` if the file is not found.

#### Attributes

| Attribute | Type | Source key | Description |
|---|---|---|---|
| `ckan_url` | `str` | `[ckan] url` | Base URL of the CKAN instance |
| `ckan_organization` | `str` | `[ckan] organization` | Default owner organization slug |
| `ckan_token` | `str` | `[ckan] api_token` | CKAN API key |
| `ckan_private` | `bool` | `[ckan] private` | Whether new datasets are private (default: `True`) |
| `sftp_address` | `str` | `[sftp] server_address` | SFTP hostname |
| `sftp_web_port` | `str` | `[sftp] server_web_port` | HTTP port for web-accessible URLs |
| `sftp_username` | `str` | `[sftp] username` | SFTP login username |
| `sftp_private_key` | `str` | `[sftp] private_key` | Absolute path to SSH private key |

#### Notes

- The settings file path is resolved with `os.path.abspath(__file__)` to avoid fragility when the script is invoked from a different working directory.
- `ckan_private` uses `configparser.getboolean()` which accepts `true`, `false`, `1`, `0`, `yes`, `no` (case-insensitive).

---

## ckan_upload.py

### Module-level constants

| Name | Value | Description |
|---|---|---|
| `ua` | `"ckan2hpc-client-0.5"` | HTTP User-Agent header sent to CKAN |

### `sha256_file(path: str) -> str`

Computes the SHA-256 hex digest of the file at `path`.

**Parameters:**

- `path` — absolute or relative path to a readable file.

**Returns:** 64-character lowercase hex string.

**Implementation:** reads the file in 8 KiB chunks to avoid loading large files into memory.

---

### `zip_directory(dirpath: str) -> str`

Recursively compresses the directory at `dirpath` into a temporary ZIP archive using DEFLATE compression.

**Parameters:**

- `dirpath` — path to the directory to compress.

**Returns:** absolute path to the temporary `.zip` file.

**Notes:**

- The archive preserves internal directory structure relative to `dirpath`.
- The caller is responsible for deleting the returned file. `ckan_upload.py` does this at cleanup.
- Uses `tempfile.NamedTemporaryFile(delete=False)` so the file persists after the handle is closed.

---

### `sanitize_dataset_name(name: str) -> str`

Converts an arbitrary string into a CKAN-compatible dataset slug.

**Parameters:**

- `name` — the raw dataset name supplied by the user.

**Returns:** lowercase string containing only `[a-z0-9_-]`, with no leading or trailing hyphens, and consecutive hyphens collapsed to one.

**Examples:**

```python
sanitize_dataset_name("Climate 2024!")  # → "climate-2024"
sanitize_dataset_name("ocean_model_v2") # → "ocean_model_v2"
sanitize_dataset_name("--bad--name--")  # → "bad-name"
```

---

### `sftp_upload(local_file: str, remote_name: str, sftp_user: str, keyfile: str) -> None`

Uploads `local_file` to `~/ckan-pub/<remote_name>` on the configured SFTP server.

**Parameters:**

- `local_file` — path to the local file to upload.
- `remote_name` — filename to use on the remote server (typically `<sha256>_<original_name>`).
- `sftp_user` — SFTP username.
- `keyfile` — path to the SSH private key.

**Behaviour:**

- Opens an SSH connection with `load_system_host_keys()` and `RejectPolicy()`.
- Displays a `tqdm` progress bar via the `paramiko` transfer callback.
- The SSH connection is always closed in a `finally` block, even on error.

**Retry:** decorated with `@retry` — up to 3 attempts, exponential back-off (2 s → up to 10 s), re-raises the last exception.

**Raises:** the last exception from `paramiko` or the OS if all retries are exhausted.

---

### `list_user_orgs(ckan: RemoteCKAN) -> list[str]`

Returns the list of CKAN organization slugs accessible to the current API token.

**Parameters:**

- `ckan` — an authenticated `RemoteCKAN` instance.

**Returns:** list of organization name strings.

**Side effects:** logs all accessible organizations at `INFO` level. Calls `exit(1)` if the token has no organization membership.

---

### `ensure_org_exists_or_fallback(ckan: RemoteCKAN, organization: str) -> str`

Validates that `organization` is accessible and returns it. If not, falls back to the first accessible organization.

**Parameters:**

- `ckan` — an authenticated `RemoteCKAN` instance.
- `organization` — the organization slug from configuration (lowercased).

**Returns:** the resolved organization slug to use as `owner_org`.

**Behaviour:**

- Calls `ckan.action.organization_show(id=organization)`.
- On `NotFound`, calls `list_user_orgs()` and returns `orgs[0]`.
- Logs the resolved organization at `INFO` level; logs the fallback at `WARNING`.

---

## ckan_download.py

### Module-level constants

| Name | Value | Description |
|---|---|---|
| `ua` | `"ckan2hpc-client-0.5"` | HTTP User-Agent header |
| `_SHA256_PREFIX` | `re.compile(r"^([0-9a-f]{64})_(.+)$")` | Pattern for filenames produced by the upload script |

---

### `_verify_sha256(path: str, expected: str) -> None`

Computes the SHA-256 of the file at `path` and compares it against `expected`.

**Parameters:**

- `path` — path to the local file to verify.
- `expected` — 64-character hex string extracted from the filename.

**Side effects:**

- Logs `INFO: SHA256 OK: <basename>` on match.
- Logs `WARNING: SHA256 MISMATCH for <basename>: expected <x>, got <y>` on mismatch.

Does not raise or exit — the caller decides how to handle a mismatch.

---

### `_maybe_verify(outfile: str) -> None`

Checks whether `outfile`'s basename matches `_SHA256_PREFIX`. If it does, calls `_verify_sha256`.

This is the single call site for post-download verification in all three download modes.

---

### `sftp_download(outfile: str, remote_file: str, sftp_user: str, keyfile: str) -> None`

Downloads `remote_file` from `~/ckan-pub/` on the SFTP server and saves it to `outfile`.

**Parameters:**

- `outfile` — absolute or relative path where the file should be saved.
- `remote_file` — filename in the remote `ckan-pub/` directory.
- `sftp_user` — SFTP username.
- `keyfile` — path to the SSH private key.

**Behaviour:**

- Opens an SSH connection with `load_system_host_keys()` and `RejectPolicy()`.
- Queries `sftp.stat(remote_file).st_size` to obtain the total for the progress bar.
- Displays a `tqdm` progress bar via the `paramiko` get callback.
- Calls `_maybe_verify(outfile)` after the download completes.
- The SSH connection is always closed in a `finally` block.

**Retry:** up to 3 attempts, exponential back-off, re-raises on exhaustion.

---

### `download_url(url: str, ckan_token: str, outfile: str) -> None`

Downloads a file from `url` using HTTP with CKAN token authentication and saves it to `outfile`.

**Parameters:**

- `url` — full HTTP/HTTPS URL of the resource.
- `ckan_token` — CKAN API token sent as the `Authorization` header.
- `outfile` — path where the downloaded file is saved.

**Behaviour:**

- Uses `requests.get(..., stream=True)` for chunked reading (1 MiB chunks).
- Uses `content-length` response header for the progress bar total when available.
- Calls `r.raise_for_status()` — HTTP 4xx/5xx responses raise `requests.HTTPError`.
- Calls `_maybe_verify(outfile)` after download completes.

**Retry:** up to 3 attempts, exponential back-off, re-raises on exhaustion.

---

### `download_dataset(ckan: RemoteCKAN, ckan_token: str, dataset: str, outdir: str) -> None`

Downloads all resources belonging to a CKAN dataset.

**Parameters:**

- `ckan` — authenticated `RemoteCKAN` instance.
- `ckan_token` — passed through to `download_url` for HTTP auth.
- `dataset` — dataset slug (name) or UUID.
- `outdir` — directory where all files are saved.

**Behaviour:** calls `package_show`, iterates `pkg["resources"]`, resolves each resource's filename from `res["name"]` or the URL path, and calls `download_url` for each.

---

### `download_resource(ckan: RemoteCKAN, ckan_token: str, resource_id: str, outdir: str) -> None`

Downloads a single resource by its UUID.

**Parameters:**

- `ckan` — authenticated `RemoteCKAN` instance.
- `ckan_token` — passed through to `download_url`.
- `resource_id` — CKAN resource UUID.
- `outdir` — directory where the file is saved.

**Behaviour:** calls `resource_show`, resolves the filename, and calls `download_url`.
