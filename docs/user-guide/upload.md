# Uploading Data

`ckan_upload.py` transfers a file or directory to HPC storage via SFTP and registers it as a resource in CKAN.

---

## Synopsis

```
python ckan_upload.py -f <path> -d <dataset-name> [-p {sftp,curl}]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `-f` | Yes | — | Path to a file or directory |
| `-d` | Yes | — | Target CKAN dataset name |
| `-p` | No | `sftp` | Transfer protocol: `sftp` or `curl` |

---

## Upload a single file

```bash
python ckan_upload.py -f results.csv -d climate-2024
```

What happens:

1. The file path is validated.
2. The dataset name `climate-2024` is sanitized to a CKAN-compatible slug (lowercase, hyphens only).
3. A SHA-256 checksum of `results.csv` is computed.
4. The file is uploaded to `~/ckan-pub/` on the HPC server as `<sha256>_results.csv`.
5. If the dataset `climate-2024` does not exist in CKAN, it is created under the configured organization.
6. A CKAN resource is registered pointing to `https://<server>:<port>/~<user>/<sha256>_results.csv`.

---

## Upload a directory

Pass a directory path with `-f`. The directory is automatically compressed to a temporary ZIP archive before transfer:

```bash
python ckan_upload.py -f ./simulation-output/ -d climate-2024
```

The ZIP is created in the system temporary directory, uploaded, registered in CKAN, and then deleted automatically. The original directory is never modified.

!!! note
    The ZIP archive preserves the internal directory structure relative to the root of the supplied path. Symlinks inside the directory are followed.

---

## Protocol options

### SFTP (default)

Recommended for all files. The file is transferred directly over SSH to the HPC storage system:

```bash
python ckan_upload.py -f data.nc -d ocean-model -p sftp
```

CKAN receives a URL pointing to the file on HPC storage. The file is never stored inside CKAN.

### CKAN API (curl)

Uploads the file body directly to CKAN via its REST API:

```bash
python ckan_upload.py -f report.pdf -d project-docs -p curl
```

!!! warning
    Use the `curl` protocol only for small files (a few hundred MB at most). CKAN's file storage is not designed for large scientific datasets. For research data, always use `sftp`.

---

## Dataset naming

CKAN requires dataset names to be URL-safe slugs: lowercase letters, digits, hyphens, and underscores only. The client automatically sanitizes the value you pass with `-d`:

| Input | Stored as |
|---|---|
| `Climate 2024` | `climate-2024` |
| `My Dataset!` | `my-dataset` |
| `ocean_model_v2` | `ocean_model_v2` *(unchanged)* |

If the name was changed, the sanitized form is logged:

```
INFO: Dataset name sanitized: 'Climate 2024' → 'climate-2024'
```

---

## Organization selection

The dataset is created under the organization specified in `settings.ini`. If that organization is not accessible with the current API token, the client falls back to the first organization available to the token and logs a warning:

```
WARNING: Organization 'physics-lab' not found or no access.
INFO: Organizations available for this user:
INFO:   - open-science
INFO:   - data-archive
INFO: Auto-fallback → using 'open-science'
```

---

## Progress and logging

During SFTP upload a real-time progress bar is displayed:

```
INFO: Uploading via SFTP
b1946ac9...a7f_results.csv:  45%|████████▌          | 450M/1.00G [00:32<00:38, 14.1MB/s]
```

After a successful resource registration:

```
INFO: New resource (proto:sftp) created!
```

---

## Retry behaviour

The SFTP transfer is retried up to **3 times** on failure, with exponential back-off starting at 2 seconds and capping at 10 seconds. Each retry attempt is logged at `WARNING` level:

```
WARNING: Retrying sftp_upload in 2.0 seconds (attempt 2 of 3) ...
```

If all three attempts fail, the error is logged and the script exits with code 1. No partial CKAN resource is registered.

---

## What is stored in CKAN

For SFTP uploads, CKAN stores:

- **Dataset** — a CKAN package with the sanitized name, owned by the resolved organization.
- **Resource** — a resource record with `name = <original filename>` and a URL pointing to the HPC-hosted file.

The dataset is created as private (`private=true`) unless configured otherwise. Nothing about the file's binary content is stored in CKAN.
