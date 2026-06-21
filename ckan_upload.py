#!/usr/bin/env python3
import os
import re
import argparse
import hashlib
import logging
import zipfile
import tempfile
import paramiko
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
from tqdm import tqdm
from ckanapi import RemoteCKAN, NotFound
from config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

ua = "ckan2hpc-client-0.5"

# ---------------- UTILITIES ----------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def zip_directory(dirpath):
    log.info("Zipping directory %s", dirpath)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()

    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                fullpath = os.path.join(root, file)
                arcname = os.path.relpath(fullpath, dirpath)
                zipf.write(fullpath, arcname)

    return tmp.name


def sanitize_dataset_name(name):
    """CKAN requires lowercase URL-safe slugs."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9_-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def sftp_upload(local_file, remote_name, sftp_user, keyfile):
    log.info("Uploading via SFTP")

    file_size = os.path.getsize(local_file)
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
    ssh.connect(
        hostname=config.sftp_address,
        username=sftp_user,
        key_filename=keyfile
    )
    try:
        sftp = ssh.open_sftp()
        sftp.chdir("ckan-pub")
        with tqdm(total=file_size, unit="B", unit_scale=True, desc=remote_name) as bar:
            sftp.put(
                local_file, remote_name,
                callback=lambda done, _total: bar.update(done - bar.n)
            )
        sftp.close()
    finally:
        ssh.close()


def list_user_orgs(ckan):
    orgs = ckan.action.organization_list_for_user()
    if not orgs:
        log.error("User does not belong to any organization!")
        exit(1)

    log.info("Organizations available for this user:")
    for org in orgs:
        log.info("  - %s", org["name"])

    return [o["name"] for o in orgs]


def ensure_org_exists_or_fallback(ckan, organization):
    try:
        ckan.action.organization_show(id=organization)
        log.info("Using organization: %s", organization)
        return organization

    except NotFound:
        log.warning("Organization '%s' not found or no access.", organization)
        orgs = list_user_orgs(ckan)
        fallback = orgs[0]
        log.info("Auto-fallback → using '%s'", fallback)
        return fallback


# ---------------- ARGUMENTS ----------------

parser = argparse.ArgumentParser(description="Upload a file or directory to CKAN via SFTP or API")
parser.add_argument("-f", dest="filepath", required=True, help="Path to file or directory to upload")
parser.add_argument("-d", dest="dataset", required=True, help="Dataset name")
parser.add_argument("-p", dest="proto", default="sftp", choices=["sftp", "curl"],
                    help="Data transfer protocol (default: sftp)")

args = parser.parse_args()

# ---------------- CONFIG (deferred until after --help) ----------------

config = Config()

# ---------------- VALIDATION ----------------

if not os.path.exists(args.filepath):
    log.error("Path does not exist: %s", args.filepath)
    exit(1)

dataset_name = sanitize_dataset_name(args.dataset)
if dataset_name != args.dataset:
    log.info("Dataset name sanitized: '%s' → '%s'", args.dataset, dataset_name)

# ---------------- CKAN CLIENT ----------------

ckan = RemoteCKAN(config.ckan_url, apikey=config.ckan_token, user_agent=ua)

# ---------------- PREPARE FILE ----------------

temp_zip = None
filepath = args.filepath

if os.path.isdir(filepath):
    temp_zip = zip_directory(filepath)
    filepath = temp_zip

filename = os.path.basename(filepath)
sha256sum = sha256_file(filepath)
remote_name = f"{sha256sum}_{filename}"

# ---------------- SFTP UPLOAD ----------------

if args.proto == "sftp":
    if not os.path.exists(config.sftp_private_key):
        log.error("Private key not found: %s", config.sftp_private_key)
        exit(1)
    try:
        sftp_upload(filepath, remote_name, config.sftp_username, config.sftp_private_key)
    except Exception as e:
        log.error("SFTP upload failed: %s", e)
        exit(1)

# ---------------- CKAN DATASET ----------------

owner_org = ensure_org_exists_or_fallback(ckan, config.ckan_organization.lower())

try:
    ckan.action.package_show(id=dataset_name)
except NotFound:
    ckan.action.package_create(
        name=dataset_name,
        owner_org=owner_org,
        private=config.ckan_private
    )

# ---------------- CKAN RESOURCE ----------------

try:
    if args.proto == "curl":
        with open(filepath, "rb") as fh:
            ckan.action.resource_create(
                package_id=dataset_name,
                name=filename,
                upload=fh,
                url="dummy"
            )
    else:
        url = (f"https://{config.sftp_address}:{config.sftp_web_port}"
               f"/~{config.sftp_username}/{remote_name}")
        ckan.action.resource_create(
            package_id=dataset_name,
            name=filename,
            url=url
        )
    log.info("New resource (proto:%s) created!", args.proto)
except Exception as e:
    log.error("Failed to create CKAN resource: %s", e)
    exit(1)

# ---------------- CLEANUP ----------------

if temp_zip:
    os.unlink(temp_zip)
