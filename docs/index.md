# CKAN2HPC Client

**Python client bridging CKAN data portals with HPC storage systems**

---

## Why CKAN2HPC?

Scientific institutions commonly use **CKAN** as a metadata catalog to describe, discover, and share datasets — while the actual data resides on **HPC storage** (cluster filesystems, object stores, or scientific storage systems). Uploading multi-gigabyte or multi-terabyte datasets directly through the CKAN web interface or API is impractical: it is slow, strains CKAN's storage backend, and bypasses the high-throughput infrastructure already available on HPC systems.

CKAN2HPC Client solves this by acting as a **bridge**:

- transfers files to HPC storage via **SFTP** using the cluster's own network path,
- registers each dataset as a resource in **CKAN** so it remains discoverable and citable through the portal,
- retrieves data back through **HTTP** (via CKAN) or **SFTP** (direct from HPC).

Large binaries never touch CKAN's storage while full metadata management, access control, and reproducibility are preserved.

---

## Current scope

CKAN2HPC Client targets institutions that run a standard CKAN instance alongside an HPC cluster accessible via SSH/SFTP. The tool is intentionally minimal: two CLI scripts backed by a shared configuration loader. It handles:

- single-file and directory uploads (directories are automatically compressed),
- SHA-256 checksum embedding for end-to-end integrity verification,
- automatic retry with exponential back-off on both upload and download paths,
- real-time progress reporting via terminal progress bars.

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/HiPERACT-Data-management/CKAN2HPC-Client.git
cd CKAN2HPC-Client
pip install -r requirements.txt

# 2. Configure (fill in your values)
cp settings.ini settings.ini.bak  # settings.ini ships as an example
nano settings.ini

# 3. Register the SFTP server in known_hosts
ssh-keyscan -p 22 <server_address> >> ~/.ssh/known_hosts

# 4. Upload a file
python ckan_upload.py -f data.csv -d my-dataset

# 5. Download it back
python ckan_download.py -m dataset -r my-dataset -d ./output/
```

---

## Documentation map

| Section | What you will find |
|---|---|
| [Installation](installation.md) | Requirements, setup, dependency overview |
| [Configuration](configuration.md) | All `settings.ini` fields with types and defaults |
| [Uploading data](user-guide/upload.md) | Upload files and directories, protocols, logging |
| [Downloading data](user-guide/download.md) | All three download modes with examples |
| [Data integrity](user-guide/integrity.md) | SHA-256 scheme, verification output, manual checks |
| [Security](security.md) | SSH keys, known_hosts, token handling, access control |
| [Architecture](developer/architecture.md) | Module map, data flows, design decisions |
| [Module reference](developer/modules.md) | Every function documented with parameters and behaviour |
| [Contributing](developer/contributing.md) | Dev setup, conventions, extension points |
