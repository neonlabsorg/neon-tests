#!/usr/bin/python

import logging
import os
import pathlib
import sys

import requests
from requests.structures import CaseInsensitiveDict

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

README = "DOCKERHUB.md"

try:
    logger.debug("Getting DHUBU, DHUBP from environment")
    username = os.environ.get("DOCKER_HUB_USER")
    password = os.environ.get("DOCKER_HUB_PASSWORD")

    if username is None or password is None:
        logger.error("Failed to get username and password from environment")
        exit(1)
    url = "https://hub.docker.com/v2/users/login"
    logger.debug("Request (post) JWT token from: " + url)
    response = requests.post(url, json={"username": username, "password": password})
    if response.status_code != 200:
        logger.error("Failed to get docker hub JWT token: {}".format(response.status_code))
        exit(1)
    token = response.json()["token"]

    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    headers["Authorization"] = "Bearer " + token
    headers["Content-Type"] = "application/json"
    logger.debug(f"Open {README}")
    with open(pathlib.Path(__file__).parent / README) as readme_file:
        readme_data = readme_file.read()
        url = "https://hub.docker.com/v2/repositories/neonlabsorg/full_test_suite/"
        logger.debug("Request (patch) to update full_description at " + url)
        response = requests.patch(url, json={"full_description": readme_data}, headers=headers)
        if response.status_code != 200:
            logger.error("Failed to patch README at neonlabsorg/full_test_suite: {}".format(response.status_code))
            exit(1)

    logger.debug("Dockerhub readme at neonlabsorg/full_test_suite updated")

except Exception as e:
    logger.error("Failed to update README at neonlabsorg/full_test_suite. Exception: {}".format(e))
    exit(1)