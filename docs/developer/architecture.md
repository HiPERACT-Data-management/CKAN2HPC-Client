# Architecture

## Module overview

CKAN2HPC Client consists of three Python modules:

```
CKAN2HPC-Client/
├── config.py          Configuration loader — reads settings.ini, exposes typed attributes
├── ckan_upload.py     Upload CLI — file/dir → SFTP + CKAN resource registration
└── ckan_download.py   Download CLI — CKAN or SFTP → local file
```

There is no shared state between the upload and download scripts beyond the configuration file. Both scripts are procedural (top-level code, no `main()` wrapper) and are intended to be invoked directly from the command line.

---

## Upload data flow

```
ckan_upload.py
│
├── argparse                         parse -f, -d, -p
├── Config()                         load settings.ini
│
├── os.path.exists(filepath)         validate input path
├── sanitize_dataset_name(dataset)   normalise to CKAN slug
│
├── [if directory] zip_directory()   compress to temp .zip
│
├── sha256_file(filepath)            compute SHA-256
│   └── remote_name = sha256 + "_" + filename
│
├── [if proto==sftp] sftp_upload()   transfer to HPC
│   ├── paramiko.SSHClient
│   │   ├── load_system_host_keys()  strict host key check
│   │   └── RejectPolicy
│   ├── sftp.chdir("ckan-pub")
│   ├── sftp.put(local, remote)      with tqdm progress
│   └── @retry (3×, exponential)    on any exception
│
├── ensure_org_exists_or_fallback()  resolve owner org
│   └── ckan.action.organization_show / organization_list_for_user
│
├── ckan.action.package_show()       check dataset existence
│   └── [NotFound] package_create() create with owner_org + private flag
│
├── ckan.action.resource_create()    register resource
│   ├── [sftp] url = https://server:port/~user/remote_name
│   └── [curl] upload = open(filepath)
│
└── [cleanup] os.unlink(temp_zip)    remove temp file if created
```

---

## Download data flow

```
ckan_download.py
│
├── argparse                         parse -m, -r, -d
├── Config()                         load settings.ini
├── os.makedirs(out_dir)             create output directory
│
├── [mode=dataset]
│   └── download_dataset()
│       ├── ckan.action.package_show(id=dataset)
│       └── for each resource:
│           └── download_url(res["url"], ...)
│
├── [mode=resource]
│   └── download_resource()
│       ├── ckan.action.resource_show(id=resource_id)
│       └── download_url(res["url"], ...)
│
├── [mode=sftp]
│   └── sftp_download(outfile, remote_file, ...)
│       ├── paramiko.SSHClient
│       │   ├── load_system_host_keys()
│       │   └── RejectPolicy
│       ├── sftp.chdir("ckan-pub")
│       ├── sftp.stat(remote) → file_size
│       ├── sftp.get(remote, local)   with tqdm progress
│       └── @retry (3×, exponential)
│
└── _maybe_verify(outfile)
    ├── regex match: ^([0-9a-f]{64})_(.+)$
    └── [match] _verify_sha256(path, expected_hash)
```

---

## Key design decisions

### SHA-256 in the filename

Embedding the checksum in the remote filename (rather than a sidecar file or database) means:

- the hash survives every system that touches the file path (CKAN metadata, HTTP URLs, SFTP directory listings),
- verification requires no additional state — only the filename and the bytes on disk,
- deduplication is implicit: identical content produces an identical remote name.

The trade-off is that the filename is long and opaque. CKAN stores the original filename as the resource `name` field, so the user-facing label remains clean.

### RejectPolicy instead of AutoAddPolicy

The original code used `paramiko.AutoAddPolicy()`, which silently accepts any host key on first connection. This was replaced with `paramiko.RejectPolicy()` combined with `load_system_host_keys()`. The client now refuses to connect to any server not already in `~/.ssh/known_hosts`.

The cost is a one-time setup step (`ssh-keyscan`). The benefit is that man-in-the-middle attacks during upload cannot succeed silently — the connection is refused outright.

### Deferred Config() initialisation

`Config()` is instantiated **after** `argparse` parses arguments. This means `--help` works even when `settings.ini` is missing or malformed. In the original code, a missing `settings.ini` caused an unhandled exception before the help text could be printed.

### Organisation fallback

If the configured organisation is inaccessible (not found, or the token lacks permission), the client falls back to the first organisation returned by `organization_list_for_user`. This makes the client usable in environments where organisation slugs are not stable (e.g., a shared development CKAN where org names change). The fallback is always logged so the user knows which organisation was used.

Critically, the resolved organisation is stored in the `owner_org` variable and passed to `package_create`. The original code re-read `config.ckan_organization` at that point, which meant the fallback was silently ignored.

### Retry with exponential back-off

SFTP and HTTP operations are wrapped with `@retry` from `tenacity`. The policy is:

- up to 3 attempts,
- wait 2 s before the second attempt, 4–10 s before the third,
- re-raise the last exception if all attempts fail (rather than wrapping it in `RetryError`).

This handles transient network issues on HPC interconnects without requiring manual re-runs for single-packet drops.

### No `main()` function

The scripts use top-level procedural code rather than a `main()` guard. This is intentional for a simple CLI tool: the scripts are not intended to be imported as modules. If the project grows to the point where functions need to be shared or tested in isolation, wrapping in `main()` and adding `if __name__ == "__main__":` is the natural next step.

---

## External dependencies

| Library | Why it was chosen |
|---|---|
| `ckanapi` | Official Python client for CKAN's action API; handles authentication headers, JSON serialisation, and error mapping (e.g., `NotFound`) |
| `paramiko` | De facto standard SSH/SFTP library for Python; supports key-based auth, progress callbacks, and programmatic known_hosts management |
| `requests` | Standard HTTP client for streaming downloads; supports chunked reading needed for progress bars and large files |
| `tenacity` | Provides composable retry decorators with fine-grained wait and stop policies; avoids hand-written retry loops |
| `tqdm` | Minimal, well-maintained progress bar library; integrates with both iterator and callback patterns used by `requests` and `paramiko` |
