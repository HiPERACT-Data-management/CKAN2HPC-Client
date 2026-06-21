# Installation

## System requirements

| Requirement | Minimum | Notes |
|---|---|---|
| Python | 3.9 | 3.10+ recommended |
| Operating system | Linux, macOS | Windows supported but not tested |
| CKAN | Any recent version | API key with write access required |
| SSH | OpenSSH or compatible | Key-based auth; server must be in `known_hosts` |

---

## 1. Clone the repository

```bash
git clone https://github.com/HiPERACT-Data-management/CKAN2HPC-Client.git
cd CKAN2HPC-Client
```

---

## 2. Create a virtual environment (recommended)

Isolating dependencies avoids conflicts with system Python packages:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate.bat    # Windows
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

### What gets installed

| Package | Version constraint | Purpose |
|---|---|---|
| `ckanapi` | latest | CKAN REST API client (dataset and resource management) |
| `paramiko` | latest | SSH/SFTP library (file transfer to HPC storage) |
| `requests` | latest | HTTP client (downloading resources via CKAN URLs) |
| `tenacity` | latest | Retry logic with exponential back-off |
| `tqdm` | latest | Terminal progress bars for upload and download |

---

## 4. Configure SSH access

CKAN2HPC Client uses **strict host key verification** — it will refuse to connect to a server whose key is not already in `~/.ssh/known_hosts`. This is a deliberate security measure to prevent man-in-the-middle attacks.

### Generate an SSH key pair (if you do not have one)

```bash
ssh-keygen -t ed25519 -C "ckan2hpc" -f ~/.ssh/id_ed25519_ckan2hpc
```

Copy the public key to the HPC server:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519_ckan2hpc.pub <username>@<server_address>
```

### Register the server in known_hosts

```bash
ssh-keyscan -p 22 <server_address> >> ~/.ssh/known_hosts
```

Verify the fingerprint is correct by comparing it with the fingerprint provided by your HPC system administrator.

---

## 5. Create settings.ini

The example `settings.ini` that ships with the repository contains placeholder values. Fill in your actual values:

```bash
nano settings.ini
```

See [Configuration](configuration.md) for a full field reference.

!!! warning
    `settings.ini` is excluded from version control by `.gitignore`. Never commit a file that contains a real API token or private key path.

---

## 6. Verify the installation

Run either script with `--help` to confirm that all imports succeed:

```bash
python ckan_upload.py --help
python ckan_download.py --help
```

Expected output for the upload script:

```
usage: ckan_upload.py [-h] -f FILEPATH -d DATASET [-p {sftp,curl}]

Upload a file or directory to CKAN via SFTP or API

options:
  -h, --help       show this help message and exit
  -f FILEPATH      Path to file or directory to upload
  -d DATASET       Dataset name
  -p {sftp,curl}   Data transfer protocol (default: sftp)
```

!!! note
    `--help` works even without a valid `settings.ini` because configuration is loaded after argument parsing.

---

## Building the documentation (optional)

To render this documentation locally:

```bash
pip install -r requirements-dev.txt
mkdocs serve
```

Open `http://127.0.0.1:8000` in a browser. To build a static HTML site:

```bash
mkdocs build          # output is written to site/
```
