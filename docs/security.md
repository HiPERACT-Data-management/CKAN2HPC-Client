# Security

This page describes the security model of CKAN2HPC Client, the assumptions it makes, and the steps required to operate it safely.

---

## Threat model

CKAN2HPC Client is designed for use within a trusted research institution's network. It assumes:

- the HPC server is operated by a trusted administrator,
- the CKAN instance is operated by a trusted administrator,
- the user's workstation is not compromised.

The client does **not** protect against:

- a compromised HPC server (once a file is uploaded, it is under the server's control),
- a compromised CKAN instance (resource URLs and metadata are at risk),
- a compromised user account (the API token and private key would be exposed).

---

## SSH host key verification

### Why this matters

By default, some SSH implementations silently accept any host key on first connection. An attacker who can intercept the connection (man-in-the-middle) could present a fraudulent key and receive the uploaded data or inject corrupted data into a download.

CKAN2HPC Client uses `paramiko.RejectPolicy()` — it **refuses** to connect to any server whose host key is not already in `~/.ssh/known_hosts`. This means first-time setup requires an explicit step, but eliminates silent MITM acceptance.

### Adding a server to known_hosts

Before first use, register the server's host key:

```bash
ssh-keyscan -p 22 <server_address> >> ~/.ssh/known_hosts
```

!!! warning
    Always verify the fingerprint out-of-band (e.g., by asking your system administrator) before trusting it. `ssh-keyscan` fetches the key from the network — it is only secure if the network path is already trusted.

Verify the fingerprint was recorded:

```bash
ssh-keygen -l -F <server_address>
```

### Updating a changed host key

If the server's host key changes (e.g., after a hardware replacement), the old key must be removed before the new one is added:

```bash
ssh-keygen -R <server_address>
ssh-keyscan -p 22 <server_address> >> ~/.ssh/known_hosts
```

---

## SSH key management

### Key generation

Use a modern key type with a dedicated key for CKAN2HPC:

```bash
ssh-keygen -t ed25519 -C "ckan2hpc-$(hostname)" -f ~/.ssh/id_ed25519_ckan2hpc
```

Using a separate key (rather than your primary key) limits exposure: if the key is compromised, it can be revoked from the HPC server without affecting other services.

### Key permissions

The private key file must be readable only by your user:

```bash
chmod 600 ~/.ssh/id_ed25519_ckan2hpc
chmod 700 ~/.ssh/
```

Paramiko will refuse to use a key file with overly permissive permissions.

### Passphrase protection

Add a passphrase to the private key for an extra layer of protection in case the key file is stolen:

```bash
ssh-keygen -p -f ~/.ssh/id_ed25519_ckan2hpc
```

If the passphrase is set, `ssh-agent` can be used to avoid re-entering it on every operation:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_ckan2hpc
```

---

## CKAN API token

### Generating a token

In CKAN, navigate to **My Account → API Tokens → Add API Token**. Give the token a descriptive name (e.g., `ckan2hpc-workstation`) so it can be identified and revoked individually.

### Token scope

Grant the minimum necessary permissions. The token must allow:

- `package_show`, `package_create` — reading and creating datasets,
- `resource_create`, `resource_show` — registering and reading resources,
- `organization_show`, `organization_list_for_user` — resolving the target organization.

### Token storage

Store the token in `settings.ini` only. Do not:

- paste it into shell history (use `nano` or a similar editor instead of `echo`),
- commit `settings.ini` to version control (it is listed in `.gitignore`),
- share it in emails, tickets, or chat.

Rotate the token periodically and immediately if it is accidentally exposed.

---

## Dataset visibility

New datasets are created as **private** by default (`private=true` in `settings.ini`). Private datasets are visible only to members of the owning CKAN organization. Set `private=false` only when the data is intended for public access.

Changing visibility of an existing dataset must be done in the CKAN interface — the client only controls the initial visibility at creation time.

---

## settings.ini protection

`settings.ini` contains both the API token and the private key path and is therefore sensitive. Protect it:

```bash
chmod 600 settings.ini
```

The file is listed in `.gitignore` to prevent accidental commits. If you use a deployment tool that copies configuration files, ensure the target has appropriate permissions and is not world-readable.
