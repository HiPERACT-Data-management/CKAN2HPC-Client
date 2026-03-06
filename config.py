import logging
import os
import configparser

class Config:
    def __init__(self):
        if not os.path.isfile(os.path.dirname(__file__) + '/settings.ini'):
            raise Exception("settings.ini does not exists")

        config = configparser.ConfigParser()
        config.read(os.path.dirname(__file__) + '/settings.ini')

        self.ckan_url = config.get('ckan', 'url')
        self.ckan_organization = config.get('ckan', 'organization')
        self.ckan_token = config.get('ckan', 'api_token')

        self.sftp_address = config.get('sftp', 'server_address')
        self.sftp_web_port = config.get('sftp', 'server_web_port')
        self.sftp_username = config.get('sftp', 'username')
        self.sftp_private_key = config.get('sftp', 'private_key')
        
