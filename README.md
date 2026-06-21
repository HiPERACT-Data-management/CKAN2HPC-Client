# CKAN2HPC Client

**Python client bridging CKAN data portals with HPC storage systems**

## Why CKAN2HPC?

Scientific institutions commonly use **CKAN** as a metadata catalog to describe, discover, and share datasets — while the actual data resides on **HPC storage** (cluster filesystems, object stores, or scientific storage systems). Uploading multi-gigabyte or multi-terabyte datasets directly through the CKAN web interface or API is impractical: it is slow, strains CKAN's storage, and bypasses the high-throughput infrastructure already available on HPC systems.

CKAN2HPC Client solves this by acting as a **bridge**:

- it transfers files to HPC storage via **SFTP** using the cluster's own network path,
- it registers each dataset as a resource in **CKAN** so it remains discoverable through the portal,
- it lets users retrieve data back through **HTTP** (via CKAN) or **SFTP** (direct).

This keeps large binaries off CKAN while preserving full metadata management, access control, and reproducibility.

### Current scope

CKAN2HPC Client targets institutions that run a standard CKAN instance alongside an HPC cluster accessible via SSH/SFTP. Transfer is handled by **Paramiko** (SFTP) and the **ckanapi** Python client. SHA-256 checksums are embedded in remote filenames for post-download integrity verification. Automatic retry with exponential back-off handles transient network issues on both upload and download paths.

------------------------------------------------------------------------

## Features

### Data upload

| Feature | Detail |
|---|---|
| File and directory upload | Directories are automatically compressed to a ZIP archive before transfer |
| Transfer protocols | SFTP (recommended for large files) or CKAN API direct upload |
| Integrity | SHA-256 checksum computed locally and embedded in the remote filename |
| Deduplication | Remote filename `<sha256>_<name>` prevents silent overwrites |
| Dataset management | Dataset created automatically if it does not exist; organization fallback if configured org is unavailable |
| Progress reporting | Real-time transfer progress bar via `tqdm` |
| Retry | Up to 3 attempts with exponential back-off on SFTP failures |

### Data download

| Mode | Description |
|---|---|
| `dataset` | Downloads all resources belonging to a CKAN dataset |
| `resource` | Downloads a single resource by its CKAN resource ID |
| `sftp` | Downloads a file directly from HPC storage via SFTP |

All download modes display a progress bar and automatically verify the SHA-256 checksum when the filename follows the `<sha256>_<name>` convention.

### Security

- SSH key authentication — no passwords stored or transmitted
- Host key verification via system `known_hosts` (rejects unknown hosts)
- CKAN API token authentication for all metadata operations
- `settings.ini` is excluded from version control by `.gitignore`

------------------------------------------------------------------------

## Architecture

```
                    +-------------------------+
                    |         User            |
                    +----------+--------------+
                               |
                               | CLI
                               v
                    +----------+--------------+
                    |    CKAN2HPC Client      |
                    +----------+--------------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
   +----------+----------+           +----------+----------+
   |         CKAN        |           |     HPC Storage     |
   |   (metadata portal) |           |  (files via SFTP)   |
   +---------------------+           +---------------------+
```

### Upload flow

```
User → ckan_upload.py
  1. Validate input path
  2. ZIP directory (if needed)
  3. Compute SHA-256 checksum
  4. Upload file to HPC via SFTP  →  ckan-pub/<sha256>_<filename>
  5. Create CKAN dataset (if missing)
  6. Register CKAN resource with URL pointing to HPC storage
```

### Download flow

```
User → ckan_download.py
  1. Query CKAN API for resource metadata
  2. Download file via HTTP (from CKAN URL) or SFTP (direct)
  3. Verify SHA-256 checksum against filename
```

------------------------------------------------------------------------

## Prerequisites

- Python **3.9** or later
- A running **CKAN** instance with API access
- An **SSH key pair** with the public key authorized on the SFTP server
- The SFTP server added to your local `~/.ssh/known_hosts`

### Adding the server to known_hosts

CKAN2HPC Client uses strict host key verification. Before first use, add the server fingerprint:

```bash
ssh-keyscan -p 22 <server_address> >> ~/.ssh/known_hosts
```

Replace `<server_address>` with the value of `server_address` in your `settings.ini`.

------------------------------------------------------------------------

## Installation

```bash
git clone https://github.com/HiPERACT-Data-management/CKAN2HPC-Client.git
cd CKAN2HPC-Client
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Configuration

Copy the example configuration and fill in your values:

```bash
cp settings.ini.example settings.ini   # or create settings.ini directly
```

`settings.ini` is excluded from version control — never commit real credentials.

### settings.ini format

```ini
[ckan]
url=https://ckan.example.com
organization=MY_ORGANIZATION
api_token=CKAN_API_TOKEN
private=true

[sftp]
server_address=hpc.example.com
server_web_port=8443
username=hpc_user
private_key=/home/user/.ssh/id_rsa
```

### Configuration reference

#### [ckan]

| Parameter | Description | Required |
|---|---|---|
| `url` | Base URL of the CKAN instance | Yes |
| `organization` | Default owner organization for new datasets | Yes |
| `api_token` | CKAN API key with write access | Yes |
| `private` | Create new datasets as private (`true` / `false`, default `true`) | No |

#### [sftp]

| Parameter | Description | Required |
|---|---|---|
| `server_address` | SFTP hostname | Yes |
| `server_web_port` | HTTP port for web-accessible file URLs | Yes |
| `username` | SFTP login username | Yes |
| `private_key` | Absolute path to SSH private key | Yes |

------------------------------------------------------------------------

## Usage

### Upload

Upload a single file to dataset `climate-2024`:

```bash
python ckan_upload.py -f data.csv -d climate-2024
```

Upload an entire directory (automatically zipped):

```bash
python ckan_upload.py -f ./results/ -d climate-2024
```

Upload via CKAN API instead of SFTP (smaller files only):

```bash
python ckan_upload.py -f data.csv -d climate-2024 -p curl
```

#### Upload arguments

| Argument | Description | Default |
|---|---|---|
| `-f` | File or directory path to upload | — |
| `-d` | Target dataset name (sanitized to a CKAN-compatible slug) | — |
| `-p` | Transfer protocol: `sftp` or `curl` | `sftp` |

### Download

Download all resources in a dataset:

```bash
python ckan_download.py -m dataset -r climate-2024 -d ./output/
```

Download a single resource by ID:

```bash
python ckan_download.py -m resource -r <resource-uuid> -d ./output/
```

Download a file directly from HPC storage via SFTP:

```bash
python ckan_download.py -m sftp -r <sha256>_data.csv -d ./output/
```

#### Download arguments

| Argument | Description | Default |
|---|---|---|
| `-m` | Download mode: `dataset`, `resource`, or `sftp` | — |
| `-r` | Dataset name, resource UUID, or SFTP filename | — |
| `-d` | Output directory | `.` (current directory) |

------------------------------------------------------------------------

## Data integrity

Every uploaded file is identified by its SHA-256 hash, which is embedded in the remote filename:

```
original:  results.csv
stored as: b1946ac92492d2347c6235b4d2611184...a7f_results.csv
```

On download, if the filename matches the `<sha256>_<name>` pattern, the client recomputes the hash of the downloaded bytes and logs a warning if they do not match. This provides end-to-end integrity verification without any additional metadata lookups.

------------------------------------------------------------------------

## Security notes

| Topic | Recommendation |
|---|---|
| SSH authentication | Use key-based authentication only; disable password auth on the server |
| Key permissions | `chmod 600 ~/.ssh/id_rsa` |
| Known hosts | Always verify the server fingerprint before first connection (`ssh-keyscan`) |
| API token | Store the token in `settings.ini` only; never hard-code it or commit it |
| Dataset visibility | New datasets are created as private by default (`private=true` in config) |

------------------------------------------------------------------------

## Troubleshooting

### `settings.ini does not exist`

Create `settings.ini` in the same directory as the scripts. See [Configuration](#configuration).

### `Server key not found in known_hosts` (SFTP connection refused)

Run `ssh-keyscan -p 22 <server_address> >> ~/.ssh/known_hosts` and retry.

### CKAN authentication error

Verify that `api_token` in `settings.ini` is valid and has write access to the target organization.

### Organization not found

If the configured organization is not accessible, the client automatically falls back to the first organization the API token has access to. Check the log output to confirm which organization was used.

### SFTP upload or download fails after retries

- Confirm `server_address` and `username` in `settings.ini`
- Confirm the private key path and permissions (`chmod 600`)
- Confirm the remote `ckan-pub/` directory exists and is writable

------------------------------------------------------------------------

## Project structure

```
CKAN2HPC-Client/
├── ckan_upload.py      # Upload CLI
├── ckan_download.py    # Download CLI
├── config.py           # Configuration loader
├── settings.ini        # Local configuration (not committed)
├── requirements.txt    # Python dependencies
├── LICENSE
├── docs/
│   ├── upload.png
│   └── download.png
└── README.md
```

------------------------------------------------------------------------

## License

MIT License — see [LICENSE](LICENSE).

Copyright (c) 2021-2026 Marcin Lawenda, Poznan Supercomputing and Networking Center
