#!/usr/bin/env python3
import os
import re
import argparse
import hashlib
import logging
import requests
from urllib.parse import urlparse

import paramiko
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
from tqdm import tqdm
from ckanapi import RemoteCKAN
from config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

ua = "ckan2hpc-client-0.5"

# Filename pattern produced by the upload script: <sha256>_<original_name>
_SHA256_PREFIX = re.compile(r"^([0-9a-f]{64})_(.+)$")


def _verify_sha256(path, expected):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual == expected:
        log.info("SHA256 OK: %s", os.path.basename(path))
    else:
        log.warning(
            "SHA256 MISMATCH for %s: expected %s, got %s",
            os.path.basename(path), expected, actual
        )


def _maybe_verify(outfile):
    m = _SHA256_PREFIX.match(os.path.basename(outfile))
    if m:
        _verify_sha256(outfile, m.group(1))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def sftp_download(outfile, remote_file, sftp_user, keyfile):
    log.info("Downloading via SFTP: %s", remote_file)

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
        file_size = sftp.stat(remote_file).st_size
        with tqdm(total=file_size, unit="B", unit_scale=True, desc=remote_file) as bar:
            sftp.get(
                remote_file, outfile,
                callback=lambda done, _total: bar.update(done - bar.n)
            )
        sftp.close()
    finally:
        ssh.close()

    _maybe_verify(outfile)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def download_url(url, ckan_token, outfile):
    log.info("Downloading %s", url)
    r = requests.get(
        url, stream=True,
        headers={"User-Agent": ua, "Authorization": ckan_token}
    )
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0)) or None
    with tqdm(total=total, unit="B", unit_scale=True, desc=os.path.basename(outfile)) as bar:
        with open(outfile, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
                bar.update(len(chunk))

    _maybe_verify(outfile)


def download_dataset(ckan, ckan_token, dataset, outdir):
    pkg = ckan.action.package_show(id=dataset)
    for res in pkg["resources"]:
        name = res["name"] or os.path.basename(urlparse(res["url"]).path)
        download_url(res["url"], ckan_token, os.path.join(outdir, name))


def download_resource(ckan, ckan_token, resource_id, outdir):
    res = ckan.action.resource_show(id=resource_id)
    name = res["name"] or os.path.basename(urlparse(res["url"]).path)
    download_url(res["url"], ckan_token, os.path.join(outdir, name))


# ---------------- ARGUMENTS ----------------

parser = argparse.ArgumentParser(description="Download datasets or resources from CKAN")
parser.add_argument("-m", dest="download_mode", required=True,
                    choices=["dataset", "resource", "sftp"],
                    help="Download mode: dataset, resource, or sftp")
parser.add_argument("-r", dest="resource", required=True,
                    help="Dataset name, resource ID, or SFTP filename")
parser.add_argument("-d", dest="out_dir", default=".", help="Output directory (default: .)")

args = parser.parse_args()

# ---------------- CONFIG (deferred until after --help) ----------------

config = Config()

# ---------------- DOWNLOAD ----------------

try:
    ckan = RemoteCKAN(config.ckan_url, apikey=config.ckan_token, user_agent=ua)

    os.makedirs(args.out_dir, exist_ok=True)

    if args.download_mode == "dataset":
        download_dataset(ckan, config.ckan_token, args.resource, args.out_dir)
    elif args.download_mode == "resource":
        download_resource(ckan, config.ckan_token, args.resource, args.out_dir)
    elif args.download_mode == "sftp":
        outfile = os.path.join(args.out_dir, args.resource)
        sftp_download(outfile, args.resource, config.sftp_username, config.sftp_private_key)

except Exception as e:
    log.error("%s", e)
    exit(1)
