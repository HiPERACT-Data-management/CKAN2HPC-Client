# Contributing

## Development environment setup

### 1. Fork and clone

```bash
git clone https://github.com/HiPERACT-Data-management/CKAN2HPC-Client.git
cd CKAN2HPC-Client
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install all dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # documentation tools
```

### 4. Verify the setup

```bash
python ckan_upload.py --help
python ckan_download.py --help
```

Both commands should print help text without errors.

---

## Code style

The project uses no formal linter configuration. Follow these conventions:

- **PEP 8** for naming and formatting. Lines up to 100 characters.
- **Logging over print**: use the module-level `log` logger (`logging.getLogger(__name__)`). Never use `print()` for diagnostic output.
- **No bare `except:`** clauses. Catch the most specific exception that makes sense.
- **No silent swallowing**: if an exception is caught and not re-raised, log it at `WARNING` or `ERROR`.
- **Exit codes**: use `exit(1)` for fatal errors, `exit(0)` (or falling off the end) for success.
- **Function comments**: only document the *why* when non-obvious. Avoid docstrings that merely restate the function name.

---

## Repository structure

```
CKAN2HPC-Client/
├── ckan_upload.py          Upload CLI
├── ckan_download.py        Download CLI
├── config.py               Configuration loader
├── settings.ini            Local configuration (gitignored)
├── requirements.txt        Runtime dependencies
├── requirements-dev.txt    Documentation build dependencies
├── mkdocs.yml              Documentation site configuration
├── LICENSE
├── README.md
└── docs/
    ├── index.md
    ├── installation.md
    ├── configuration.md
    ├── security.md
    ├── user-guide/
    │   ├── upload.md
    │   ├── download.md
    │   └── integrity.md
    └── developer/
        ├── architecture.md
        ├── modules.md
        └── contributing.md (this file)
```

---

## Adding a new download mode

Download modes are dispatched by a simple `if/elif` chain at the bottom of `ckan_download.py`. To add a mode:

1. Implement a function following the pattern of `download_dataset` or `download_resource`:

    ```python
    def download_mymode(ckan, ckan_token, identifier, outdir):
        # resolve the file URL or path
        # call download_url() or sftp_download()
    ```

2. Add `"mymode"` to the `choices` list on the `-m` argument:

    ```python
    parser.add_argument("-m", dest="download_mode", required=True,
                        choices=["dataset", "resource", "sftp", "mymode"], ...)
    ```

3. Add a branch in the dispatch block:

    ```python
    elif args.download_mode == "mymode":
        download_mymode(ckan, config.ckan_token, args.resource, args.out_dir)
    ```

4. Document the new mode in `docs/user-guide/download.md`.

---

## Adding a new upload protocol

Upload protocols are dispatched by the `-p` argument. To add a protocol:

1. Implement a transfer function. For SFTP, follow `sftp_upload`. For HTTP-based protocols, use `requests`.

2. Add the protocol name to `choices` on the `-p` argument.

3. Add the transfer call in the SFTP UPLOAD section of `ckan_upload.py` and the corresponding CKAN resource registration in the CKAN RESOURCE section.

4. Document it in `docs/user-guide/upload.md`.

---

## Extending the configuration

To add a new configuration option:

1. Add a `self.<attr>` assignment in `Config.__init__` using `config.get()`, `config.getint()`, or `config.getboolean()` with a sensible `fallback` for optional fields.

2. Update `settings.ini` with the new key and an example value.

3. Document the field in `docs/configuration.md`.

---

## Building and previewing documentation

```bash
# Serve locally with live reload
mkdocs serve

# Build static HTML
mkdocs build
```

The static site is written to `site/`. Do not commit the `site/` directory — add it to `.gitignore` if needed.

---

## Commit conventions

- Write commit messages in the imperative mood: *"Add retry logic"*, not *"Added retry logic"*.
- Keep the subject line under 72 characters.
- Use the body to explain *why*, not *what* — the diff already shows what changed.
- Reference issue numbers where applicable.

---

## Reporting issues

Open an issue on [GitHub](https://github.com/HiPERACT-Data-management/CKAN2HPC-Client/issues) with:

- the command you ran,
- the full log output (set `logging.basicConfig(level=logging.DEBUG, ...)` for verbose output),
- the Python and library versions (`pip freeze`),
- the operating system.

Do not include API tokens or private key contents in issue reports.
