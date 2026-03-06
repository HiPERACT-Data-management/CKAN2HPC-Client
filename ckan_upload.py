#!/usr/bin/env python3
import os
import argparse
import hashlib
import zipfile
import tempfile
import paramiko
from ckanapi import RemoteCKAN, NotFound
from config import Config

# ---------------- CONFIG ----------------
config = Config()
ua = "upload-client-0.4"

# ---------------- UTILITIES ----------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def zip_directory(dirpath):
    print(f"Zipping directory {dirpath}")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()

    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                fullpath = os.path.join(root, file)
                arcname = os.path.relpath(fullpath, dirpath)
                zipf.write(fullpath, arcname)

    return tmp.name


def sftp_upload(local_file, remote_name, sftp_user, keyfile):
    print("Uploading via SFTP")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=config.sftp_address,
        username=sftp_user,
        key_filename=keyfile
    )

    sftp = ssh.open_sftp()
    sftp.chdir("ckan-pub")
    sftp.put(local_file, remote_name)
    sftp.close()
    ssh.close()

def list_user_orgs(ckan):
    orgs = ckan.action.organization_list_for_user()
    if not orgs:
        print("User does not belong to any organization!")
        exit(1)

    print("\nOrganizations available for this user:")
    for org in orgs:
        print(" -", org["name"])

    return [o["name"] for o in orgs]


def ensure_org_exists_or_fallback(ckan, organization):
    """
    If org exists → use it
    If not → fallback to first available organization
    """
    try:
        ckan.action.organization_show(id=organization)
        print(f"Using organization: {organization}")
        return organization

    except NotFound:
        print(f"\nOrganization '{organization}' not found or no access.")
        orgs = list_user_orgs(ckan)

        fallback = orgs[0]
        print(f"Auto-fallback → using '{fallback}'\n")
        return fallback
    

# ---------------- ARGUMENTS ----------------

parser = argparse.ArgumentParser()
parser.add_argument("-f", dest="filepath", required=True, help="Path to the file to upload")
parser.add_argument("-d", dest="dataset", required=True, help="Dataset name")
parser.add_argument("-p", dest="proto", default="sftp", help="Data transfer protocol")

args = parser.parse_args()

# ---------------- CKAN ----------------

ckan = RemoteCKAN(
    config.ckan_url,
    apikey=config.ckan_token,
    user_agent=ua
)

# ---------------- UPLOAD ----------------

if not args.filepath:
    print("No input path")
    exit()

if not args.dataset:
    print("No input dataset")
    exit()

if not os.path.exists(args.filepath):
    print("File to upload does not exist")
    exit()

temp_zip = None
filepath = args.filepath

if os.path.isdir(filepath):
    temp_zip = zip_directory(filepath)
    filepath = temp_zip

filename = os.path.basename(filepath)
sha256sum = sha256_file(filepath)
remote_name = f"{sha256sum}_{filename}"

# ---------------- SFTP ----------------

if args.proto == "sftp":
    if not os.path.exists(config.sftp_private_key):
        print("Check your private key file: ", config.sftp_private_key)
        exit()
    try:
        sftp_upload(filepath, remote_name, config.sftp_username, config.sftp_private_key)
    except Exception as e:
        print(e)
        exit()

# ---------------- CKAN DATASET ----------------

owner_org = ensure_org_exists_or_fallback(ckan, config.ckan_organization.lower())

try:
    ckan.action.package_show(id=args.dataset)
except NotFound:
    ckan.action.package_create(
        name=args.dataset,
        owner_org=config.ckan_organization.lower(),
        private=True
    )

# ---------------- CKAN RESOURCE ----------------
try:
    if args.proto == "curl":
        ckan.action.resource_create(
            package_id=args.dataset,
            name=filename,
            upload=open(filepath, "rb"),
            url="dummy"
        )
    else:
        url = f"https://{config.sftp_address}:{config.sftp_web_port}/~{config.sftp_username}/{remote_name}"
        ckan.action.resource_create(
            package_id=args.dataset,
            name=filename,
            url=url
        )

    print("New resource (proto:{0}) created!".format(args.proto))
except Exception as e:
    print(e)

# ---------------- CLEANUP ----------------
if temp_zip:
    os.unlink(temp_zip)
