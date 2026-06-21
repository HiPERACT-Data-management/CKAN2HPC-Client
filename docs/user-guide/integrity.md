# Data Integrity

CKAN2HPC Client provides end-to-end integrity verification using SHA-256 checksums embedded directly in remote filenames. No separate checksum database or manifest file is required.

---

## How it works

### At upload time

When a file is uploaded, its SHA-256 hash is computed locally before the transfer begins. The remote filename is constructed as:

```
<sha256_hex>_<original_filename>
```

Example:

```
original:   results.csv
stored as:  b1946ac92492d2347c6235b4d2611184ad2d4f4c3b7e4c90a2f4c8d3e1f0a2b_results.csv
```

This name is used:

- as the filename on HPC storage under `~/ckan-pub/`,
- in the CKAN resource URL,
- as the CKAN resource name displayed in the portal.

Because the hash is embedded in the filename, it travels with the file through every system that handles it: CKAN metadata, HTTP URLs, and direct SFTP paths all carry the expected checksum.

### At download time

After each file is downloaded (by any mode), the client inspects the saved filename. If it matches the pattern `[0-9a-f]{64}_<name>`, the 64-character prefix is treated as the expected SHA-256 hash. The client recomputes the hash over the downloaded bytes and compares:

**Match:**
```
INFO: SHA256 OK: results.csv
```

**Mismatch:**
```
WARNING: SHA256 MISMATCH for results.csv: expected b1946a..., got 3d7f2c...
```

A mismatch does not abort the process — the file is kept and the warning is logged. The decision of what to do with a corrupted file is left to the user.

---

## Collision prevention

Because the SHA-256 hash of the file's content is part of the remote filename, two files with identical names but different contents will produce different remote filenames and will not overwrite each other. Two files with identical contents will produce the same remote filename, which is safe: they are bitwise identical by definition.

---

## Verifying a file manually

If you want to re-verify a downloaded file at any time:

```bash
sha256sum results.csv
```

Compare the output against the 64-character prefix of the filename used during upload. They must match exactly.

On macOS:

```bash
shasum -a 256 results.csv
```

---

## Limitations

- Verification is **opportunistic**: it only triggers when the local filename follows the `<sha256>_<name>` convention. Files downloaded via the `dataset` or `resource` modes may have been given a plain name in CKAN (e.g., `results.csv` without a hash prefix), in which case no verification occurs.
- The client does not prevent overwriting an existing local file with a corrupted download. Always use a fresh output directory for critical data.
- Verification covers **data integrity in transit**, not **authenticity**. It cannot detect whether the original file on HPC storage was tampered with before upload.
