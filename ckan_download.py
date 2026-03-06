#!/usr/bin/env python3
import os
import argparse
import requests
from urllib.parse import urlparse

import paramiko
from ckanapi import RemoteCKAN, NotFound
from config import Config

# ---------------- CONFIG ----------------
config = Config()
ua = "upload-client-0.4"

def sftp_download(outfile, remote_file, sftp_user, keyfile):
    print("Downloading via SFTP")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=config.sftp_address,
        username=sftp_user,
        key_filename=keyfile
    )

    sftp = ssh.open_sftp()
    sftp.chdir("ckan-pub")
    sftp.get(remote_file, outfile)
    sftp.close()
    ssh.close()


def download_url(url, ckan_token, outfile):
    print("Downloading", url)
    r = requests.get(url, stream=True, headers={"User-Agent": ua, "Authorization": ckan_token})
    r.raise_for_status()
    with open(outfile, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            f.write(chunk)


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

parser = argparse.ArgumentParser()
parser.add_argument("-m", dest="download_mode", required=True, help="Download mode: [dataset, resource, sftp]")
parser.add_argument("-r", dest="resource", required=True, help="Resource: dataset name, resource id, file name")
parser.add_argument("-d", dest="out_dir", default=".", help="Output directory")

args = parser.parse_args()

# ---------------- CKAN ----------------
try:

    ckan = RemoteCKAN(
        config.ckan_url,
        apikey=config.ckan_token,
        user_agent=ua
    )

# ---------------- DOWNLOAD MODES ----------------
    os.makedirs(args.out_dir, exist_ok=True)

    if args.download_mode == "dataset":
        download_dataset(ckan, config.ckan_token, args.resource, args.out_dir)
    elif args.download_mode == "resource":
        download_resource(ckan, config.ckan_token, args.resource, args.out_dir)
    elif args.download_mode == "sftp":
        os.chdir(args.out_dir)
        sftp_download(args.resource, args.resource, config.sftp_username, config.sftp_private_key)
    else:
        print("Invalid download mode")
        exit()
except Exception as e:
    print(e)
