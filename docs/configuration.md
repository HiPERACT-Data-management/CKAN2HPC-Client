# Configuration

All settings are stored in a single INI file named `settings.ini`, located in the same directory as the scripts. The file must exist before either script can run — creating it is the first step after installation.

---

## File format

`settings.ini` uses standard INI syntax, parsed by Python's `configparser` module. Two sections are required: `[ckan]` and `[sftp]`.

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
private_key=/home/user/.ssh/id_ed25519_ckan2hpc
```

---

## [ckan] section

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `url` | string | Yes | — | Base URL of the CKAN instance, without a trailing slash |
| `organization` | string | Yes | — | Name (slug) of the CKAN organization that owns new datasets |
| `api_token` | string | Yes | — | CKAN API key; must have write access to the organization |
| `private` | boolean | No | `true` | Whether newly created datasets are private (`true`) or public (`false`) |

### url

Must include the scheme and host; no trailing slash:

```ini
url=https://ckan.my-institution.pl
```

### organization

Use the organization's **slug** (URL identifier), not its display name. Find it in the organization's CKAN page URL:

```
https://ckan.example.com/organization/my-org-slug
                                       ^^^^^^^^^^^^^
```

If the configured organization is not accessible, the client automatically falls back to the first organization the API token has access to and logs a warning.

### api_token

Generate a token in CKAN at **My Account → API Tokens → Add API Token**. The token must have permission to:

- create and read datasets (`package_create`, `package_show`),
- create resources (`resource_create`),
- read organization membership (`organization_list_for_user`, `organization_show`).

### private

Controls the visibility of **newly created** datasets. Existing datasets are not affected.

```ini
private=true    # dataset visible only to organization members (default)
private=false   # dataset publicly visible
```

---

## [sftp] section

| Parameter | Type | Required | Description |
|---|---|---|---|
| `server_address` | string | Yes | Hostname or IP address of the SFTP server |
| `server_web_port` | integer | Yes | HTTPS port through which stored files are accessible via HTTP |
| `username` | string | Yes | SFTP login username |
| `private_key` | string | Yes | Absolute path to the SSH private key file |

### server_address

The hostname used for both SFTP connections and the resource URL registered in CKAN:

```ini
server_address=hpc.my-institution.pl
```

This host must be present in `~/.ssh/known_hosts`. See [Security — known_hosts](security.md#known_hosts) for setup instructions.

### server_web_port

After a file is uploaded to `ckan-pub/` on the HPC server, CKAN stores a URL of the form:

```
https://<server_address>:<server_web_port>/~<username>/<sha256>_<filename>
```

Set this to the HTTPS port that serves the `public_html` or `ckan-pub` directory:

```ini
server_web_port=8443
```

### username

The SFTP username. Files are placed in `~/ckan-pub/` on the remote server under this user's home directory.

### private_key

Absolute path to the SSH private key. The corresponding public key must be authorized on the server:

```ini
private_key=/home/myuser/.ssh/id_ed25519_ckan2hpc
```

The key file must have permissions `600`:

```bash
chmod 600 /home/myuser/.ssh/id_ed25519_ckan2hpc
```

---

## Example configurations

### Research cluster (recommended setup)

```ini
[ckan]
url=https://data.institution.pl
organization=physics-department
api_token=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
private=true

[sftp]
server_address=hpc.institution.pl
server_web_port=8443
username=jsmith
private_key=/home/jsmith/.ssh/id_ed25519_ckan2hpc
```

### Public dataset workflow

```ini
[ckan]
url=https://opendata.institution.pl
organization=open-science
api_token=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
private=false

[sftp]
server_address=storage.institution.pl
server_web_port=443
username=datauser
private_key=/home/datauser/.ssh/id_rsa
```

---

## Security notes

- `settings.ini` is listed in `.gitignore` and must never be committed to version control.
- If you need to share configuration templates, use a `settings.ini.example` file with placeholder values.
- Rotate CKAN API tokens periodically and immediately if a token is accidentally exposed.
