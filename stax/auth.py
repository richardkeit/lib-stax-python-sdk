#!/usr/local/bin/python3
import logging
import sys
from datetime import date, datetime, timedelta, timezone

import boto3
from aws_requests_auth.aws_auth import AWSRequestsAuth
from botocore import UNSIGNED
from botocore.client import Config as BotoConfig
from warrant import Cognito

from stax.config import Config as JumaConfig


class StaxAuth:
    def __init__(self, config_branch):
        config = JumaConfig.api_config

        self.identity_pool = config.get(config_branch).get("identityPoolId")
        self.user_pool = config.get(config_branch).get("userPoolId")
        self.client_id = config.get(config_branch).get("userPoolWebClientId")
        self.aws_region = config.get(config_branch).get("region")

    def requests_auth(self, username, password):
        id_token = self.id_token_from_cognito(username, password)
        id_creds = self.sts_from_cognito_identity_pool(id_token)
        auth = self.sigv4_signed_auth_headers(id_creds)

        JumaConfig.expiration = id_creds.get("Credentials").get("Expiration")
        JumaConfig.auth = auth

        return JumaConfig.auth

    def id_token_from_cognito(self, username, password):
        u = Cognito(self.user_pool, self.client_id, username=username)
        u.authenticate(password=password)
        # logging.debug(f"TOK: {u.id_token}")
        return u.id_token

    def sts_from_cognito_identity_pool(self, token):
        cognito = boto3.client(
            "cognito-identity", config=BotoConfig(signature_version=UNSIGNED)
        )
        id = cognito.get_id(
            IdentityPoolId=self.identity_pool,
            Logins={
                f"cognito-idp.{self.aws_region}.amazonaws.com/{self.user_pool}": token
            },
        )
        # logging.debug(f"ID: {id}")

        id_creds = cognito.get_credentials_for_identity(
            IdentityId=id["IdentityId"],
            Logins={
                f"cognito-idp.{self.aws_region}.amazonaws.com/{self.user_pool}": token
            },
        )
        # logging.debug(f"CREDS: {id_creds}")
        return id_creds

    def sigv4_signed_auth_headers(self, id_creds):
        auth = AWSRequestsAuth(
            aws_access_key=id_creds.get("Credentials").get("AccessKeyId"),
            aws_secret_access_key=id_creds.get("Credentials").get("SecretKey"),
            aws_token=id_creds.get("Credentials").get("SessionToken"),
            aws_host=f"{JumaConfig.hostname}",
            aws_region=self.aws_region,
            aws_service="execute-api",
        )
        # logging.debug(f"AUTH: {auth}")
        return auth


class RootAuth:
    @staticmethod
    def requests_auth(username, password):
        if JumaConfig.expiration and JumaConfig.expiration > datetime.now(timezone.utc):
            return JumaConfig.auth

        return StaxAuth("JumaAuth").requests_auth(username, password)


class ApiTokenAuth:
    @staticmethod
    def requests_auth(username, password):
        if JumaConfig.expiration and JumaConfig.expiration > datetime.now(timezone.utc):
            return JumaConfig.auth

        return StaxAuth("ApiAuth").requests_auth(username, password)
