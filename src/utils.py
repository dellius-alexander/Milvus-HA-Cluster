#!/usr/bin/env python3
# File: src.utils.py
import base64
import hashlib
import hmac
import json
import os
from functools import wraps
from typing import Any

# from PIL import Image
from cryptography.fernet import Fernet

from src.logger import getLogger as GetLogger

# Logging setup
log = GetLogger(__name__)

# Custom function decorator to log function calls
def async_log_decorator(func):
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


# Custom function decorator to log function calls
def log_decorator(func):
    """Decorator for logging operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        log.debug(f"Starting function: {func.__name__},"
                  f"\nArgs: \nn{args}"
                  f"\nKwargs: \n{kwargs}")
        result = func(*args, **kwargs)
        log.debug(f"Result: \n{result}")
        log.debug(f"Completed function: {func.__name__}")
        return result
    return wrapper


# Configuration Management
class ConfigManager:
    """Manages Milvus configuration settings from a file or environment variables.

    Attributes:
        config (Dict): Configuration dictionary with host, port, user, password, etc.

    """

    config: dict[str, Any] = None

    def __init__(self, config_file: str or dict = "config.json"):
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

    @log_decorator
    def _load_config(self, config_file: str) -> dict:
        """Load configuration from file or environment variables.

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
            "encryption_key": base64.urlsafe_b64encode(os.urandom(32))
        }
        log.info(f"Default config: {json.dumps(defaults, indent=2, default=str)}")
        if isinstance(config_file, dict):
            # config_file = json.dumps(config_file)
            return config_file
        if os.path.exists(config_file):
            with open(config_file) as f:
                config = json.load(f)
                defaults.update(config)
        for key in defaults:
            defaults[key] = os.getenv(key.upper(), defaults[key])
        return defaults

    @log_decorator
    def get(self, key: str) -> Any:
        """Get a configuration value.

        Args:
            key (str): Configuration key.

        Returns:
            Any: Configuration value.

        """
        return self.config.get(key)

    def __str__(self):
        """String representation of the ConfigManager."""
        return f"ConfigManager(config={self.config})"

    def __repr__(self):
        """String representation of the ConfigManager."""
        return f"ConfigManager(config={self.config})"

    def __dict__(self):
        """Dictionary representation of the ConfigManager."""
        return self.config


# Security Utilities
class SecurityManager:
    """Handles encryption, authentication, and authorization.

    Attributes:
        cipher (Fernet): Fernet cipher for encryption/decryption.

    """

    cipher: Fernet = None
    config: ConfigManager = None

    def __init__(self, config: ConfigManager):
        """Initialize with an encryption key.

        Args:
            config (ConfigManager): Configuration manager instance.

        The encryption key should be a 32-byte URL-safe base64-encoded key.

        Raises:
            ValueError: If the encryption key is not valid.

        """
        self.cipher = Fernet(config.get("encryption_key"))
        self.config = config

    @log_decorator
    def encrypt(self, data: str) -> str:
        """Encrypt data.

        Args:
            data (str): Data to encrypt.

        Returns:
            str: Encrypted data.

        """
        return self.cipher.encrypt(data.encode()).decode()

    @log_decorator
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data.

        Args:
            encrypted_data (str): Encrypted data.

        Returns:
            str: Decrypted data.

        """
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    @log_decorator
    def hash_password(self, password: str, key: bytes) -> str:
        """Hash a password.

        Args:
            password (str): Password to hash.
            key (bytes): Key for hashing.

        Returns:
            str: Hashed password.

        """
        return hmac.new(key, password.encode(), hashlib.sha256).hexdigest()

    @log_decorator
    def authorize(self, user: str, action: str) -> bool:
        """Authorize an action for a user.

        Args:
            user (str): Username.
            action (str): Action to authorize.

        Returns:
            bool: True if authorized, False otherwise.

        """
        roles = {"admin": ["all"], "user": ["read", "write"]}
        user_role = "admin" if user == self.config.get("user") else "user"
        return "all" in roles[user_role] or action in roles[user_role]

    def __str__(self):
        """String representation of the SecurityManager."""
        return f"SecurityManager(encryption_key={self.config.get('encryption_key')})"

    def __repr__(self):
        """String representation of the SecurityManager."""
        return f"SecurityManager(encryption_key={self.config.get('encryption_key')})"

    def __dict__(self):
        """Dictionary representation of the SecurityManager."""
        return {
            "encryption_key": self.config.get("encryption_key"),
            "cipher": self.cipher
        }


# def resize_image(input_path, output_path, new_width, new_height):
#     try:
#         # Check if the input file exists
#         if not os.path.exists(input_path):
#             raise FileNotFoundError(f"The input file {input_path} does not exist.")
#
#         # Check if the input file is a valid image
#         if not input_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
#             raise ValueError(f"The input file {input_path} is not a valid image format.")
#
#         # Check if the output directory exists, create it if not
#         output_dir = os.path.dirname(output_path)
#         if not os.path.exists(output_dir):
#             os.makedirs(output_dir)
#
#         # Open the image
#         image = Image.open(input_path)
#
#         # Resize the image
#         resized_image = image.resize((new_width, new_height), Image.Resampling.HAMMING)
#
#         # Save the resized image
#         resized_image.save(output_path, format='PNG')
#         log.info(f"Image resized to {new_width}x{new_height} and saved as {output_path}")
#     except Exception as e:
#         log.error(f"Error resizing image: {e}")


# # Example usage
# if __name__ == "__main__":
#     config_manager = ConfigManager()
#     log.info(f"ConfigManager: \n {json.dumps(config_manager.config, indent=2, default=str)}")
#     security_manager = SecurityManager(
#         config=config_manager
#     )
#     log.info(f"SecurityManager: \n {security_manager}")
#     encrypted_data = security_manager.encrypt("sensitive data")
#     log.info(f"Encrypted Data: {encrypted_data}")
#     decrypted_data = security_manager.decrypt(encrypted_data)
#     log.info(f"Decrypted Data: {decrypted_data}")
#     hashed_password = security_manager.hash_password("password", config_manager.get("encryption_key"))
#     log.info(f"Hashed Password: {hashed_password}")
