# Downloading Data

`ckan_download.py` retrieves datasets or individual resources from CKAN, or downloads files directly from HPC storage via SFTP.

---

## Synopsis

```
python ckan_download.py -m <mode> -r <identifier> [-d <output-dir>]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `-m` | Yes | — | Download mode: `dataset`, `resource`, or `sftp` |
| `-r` | Yes | — | Dataset name, resource UUID, or SFTP filename |
| `-d` | No | `.` (current directory) | Output directory |

The output directory is created automatically if it does not exist.

---

## Mode: dataset

Downloads **all resources** belonging to a CKAN dataset. Use the dataset's slug name (same value passed to `-d` during upload).

```bash
python ckan_download.py -m dataset -r climate-2024 -d ./downloads/
```

What happens:

1. The CKAN API is queried for the dataset package (`package_show`).
2. Each resource's URL and name are retrieved.
3. Every resource file is downloaded to the output directory.
4. SHA-256 is verified for each file whose name matches the `<sha256>_<name>` pattern.

This mode is most useful for reproducing a complete analysis: all input files can be retrieved in one command.

---

## Mode: resource

Downloads a **single resource** by its CKAN resource UUID.

```bash
python ckan_download.py -m resource -r 3f8a2c1d-4e5b-4f0c-9a1b-2d3e4f5a6b7c -d ./downloads/
```

Find the resource UUID on the CKAN dataset page, or from the URL:

```
https://ckan.example.com/dataset/climate-2024/resource/3f8a2c1d-...
                                                        ^^^^^^^^^^^
```

What happens:

1. The CKAN API is queried for resource metadata (`resource_show`).
2. The resource's stored URL is retrieved and the file is downloaded via HTTP.
3. SHA-256 is verified if the filename matches the upload convention.

---

## Mode: sftp

Downloads a file **directly from HPC storage** via SFTP, bypassing CKAN entirely. Use this when:

- the CKAN HTTP endpoint is unavailable,
- you know the exact remote filename and want the fastest path,
- you are on the same network as the HPC system.

```bash
python ckan_download.py -m sftp -r b1946ac9...a7f_results.csv -d ./downloads/
```

The `-r` argument must be the **exact remote filename** (including the SHA-256 prefix) as it exists in `~/ckan-pub/` on the HPC server.

What happens:

1. An SFTP connection is established to the configured server.
2. The client changes to `ckan-pub/` on the remote.
3. The file is downloaded to `<output-dir>/<filename>`.
4. SHA-256 is verified against the hash embedded in the filename.

---

## Progress bars

All download modes show a real-time progress bar:

```
INFO: Downloading https://hpc.example.com:8443/~jsmith/b1946...csv
results.csv:  72%|█████████████████▉       | 720M/1.00G [00:51<00:19, 14.8MB/s]
INFO: SHA256 OK: results.csv
```

If the server does not provide a `content-length` header, the progress bar runs without a total and shows bytes received instead of a percentage.

---

## Retry behaviour

HTTP and SFTP downloads are retried up to **3 times** on failure, with exponential back-off starting at 2 seconds and capping at 10 seconds:

```
WARNING: Retrying download_url in 4.0 seconds (attempt 2 of 3) ...
```

If all three attempts fail, the script exits with code 1.

---

## Integrity verification

After every download, the client checks whether the local filename matches the SHA-256 upload convention. If it does, the checksum is recomputed and compared. See [Data Integrity](integrity.md) for details.
