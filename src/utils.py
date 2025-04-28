#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/utils.py
import base64
import hashlib
import json
import os
from functools import wraps
from typing import Any, Dict
from cryptography.fernet import Fernet
from src.logger import getLogger as GetLogger


# Logging setup
log = GetLogger(__name__)

# Custom function decorator to log function calls
def log_decorator(func):
    """Decorator for logging operations."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        log.debug(f"Starting function: {func.__name__},"
                  f"\nArgs: {args}"
                  f"\nKwargs: {kwargs}")
        result = await func(*args, **kwargs)
        log.debug(f"Completed function: {func.__name__}")
        return result
    return wrapper

# Configuration Management
class ConfigManager:
    """
    Manages configuration settings from a file or environment variables.

    Attributes:
        config (Dict): Configuration dictionary with host, port, user, password, etc.
    """
    def __init__(self, config_file: str = "config.json"):
        """Initialize with a config file path.

        Args:
            config_file (str): Path to the configuration file.

        If the file does not exist, default values are used.

        The default values are:

            - defaults = {
            "host": "localhost",
            "port": "19530",
            "user": "milvus",
            "password": "developer",
            "timeout": 30,
            "db_name": "default",
            "encryption_key": base64.urlsafe_b64encode(b"32byteslongkeyforfernetencryption!")
            }


        """
        self.config = self._load_config(config_file)

    def _load_config(self, config_file: str) -> Dict:
        """
        Load configuration from file or environment variables.

        Args:
            config_file (str): Path to the configuration file.

        Returns:
            Dict: Configuration dictionary.
        """
        defaults = {
            "host": "127.0.0.1",
            "port": "19530",
            "user": "milvus",
            "password": "developer",
            "timeout": 30,
            "db_name": "default",
            "encryption_key": base64.urlsafe_b64encode(b"32byteslongkeyforfernetencryption!")
        }
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                defaults.update(config)
        for key in defaults:
            defaults[key] = os.getenv(key.upper(), defaults[key])
        return defaults

    def get(self, key: str) -> Any:
        """
        Get a configuration value.

        Args:
            key (str): Configuration key.

        Returns:
            Any: Configuration value.
        """
        return self.config.get(key)


# Security Utilities
class SecurityManager:
    """
    Handles encryption, authentication, and authorization.

    Attributes:
        cipher (Fernet): Fernet cipher for encryption/decryption.
    """
    def __init__(self, encryption_key: bytes, config: ConfigManager):
        """Initialize with an encryption key.

        Args:
            encryption_key (bytes): Encryption key for Fernet.
            config (ConfigManager): Configuration manager instance.

        The encryption key should be a 32-byte URL-safe base64-encoded key.

        Raises:
            ValueError: If the encryption key is not valid.

        """
        self.cipher = Fernet(encryption_key)
        self.config = config

    def encrypt(self, data: str) -> str:
        """
        Encrypt data.

        Args:
            data (str): Data to encrypt.

        Returns:
            str: Encrypted data.
        """
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data.

        Args:
            encrypted_data (str): Encrypted data.

        Returns:
            str: Decrypted data.
        """
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def hash_password(self, password: str) -> str:
        """
        Hash a password.

        Args:
            password (str): Password to hash.

        Returns:
            str: Hashed password.
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def authorize(self, user: str, action: str) -> bool:
        """
        Authorize an action for a user.

        Args:
            user (str): Username.
            action (str): Action to authorize.

        Returns:
            bool: True if authorized, False otherwise.
        """
        roles = {"admin": ["all"], "user": ["read", "write"]}
        user_role = "admin" if user == self.config.get("user") else "user"
        return "all" in roles[user_role] or action in roles[user_role]
