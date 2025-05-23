import dotenv
import pytest
import json
import base64
from unittest.mock import patch
from src.utils import ConfigManager, SecurityManager
import os
import dotenv
from src.logger import getLogger as GetLogger

log = GetLogger(__name__)


# Test fixtures and setup
@pytest.fixture
def tmp_path():
    curr_dir = os.path.dirname(__file__)
    os.makedirs(os.path.join(curr_dir, "tmp"), exist_ok=True)
    temp_dir = os.path.join(curr_dir, "tmp")
    yield str(temp_dir)

@pytest.fixture
def temp_config_file(tmp_path):
    config = {
        "host": "test.milvus.com",
        "port": "9999",
        "user": "testuser",
        "password": "testpass",
        "timeout": 60,
        "db_name": "test_db"
    }
    dotenv.load_dotenv(
        dotenv_path=os.path.join(tmp_path, "test.env"),
        verbose=True,
        override=True)
    config_file = os.path.join(tmp_path, "config.json")
    with open(config_file, 'w') as file:
        json.dump(config, file, indent=2)
    return str(config_file)

@pytest.fixture
def config_manager(temp_config_file):
    return ConfigManager(temp_config_file)

@pytest.fixture
def encryption_key():
    return base64.urlsafe_b64encode(b"32byteslongkeyforfernetencryption!")


@pytest.fixture
def security_manager(config_manager):
    return SecurityManager(config_manager)

###########################################################
# ConfigManager Tests
class TestConfigManager:
    def test_init_with_existing_config(self, temp_config_file):
        cm = ConfigManager(temp_config_file)
        assert cm.config["host"] == "test.milvus.com"
        assert cm.config["port"] == "9999"
        assert cm.config["user"] == "testuser"
        assert cm.config["password"] == "testpass"
        assert cm.config["timeout"] == '60'
        assert cm.config["db_name"] == "test_db"

    @patch.dict(os.environ, {
        "HOST": "127.0.0.1",
        "PORT": "19530",
        "USER": "milvus",
        "PASSWORD": "developer",
        "TIMEOUT": "30",
        "DB_NAME": "default"
    })
    def test_init_with_nonexistent_config(self):
        cm = ConfigManager("nonexistent.json")
        assert cm.config["host"] == "127.0.0.1"
        assert cm.config["port"] == "19530"
        assert cm.config["user"] == "milvus"
        assert cm.config["password"] == "developer"
        assert cm.config["timeout"] == "30"
        assert cm.config["db_name"] == "default"

    @patch.dict(os.environ, {
        "HOST": "env.milvus.com",
        "PORT": "8888",
        "USER": "envuser",
        "PASSWORD": "testpass",
    })
    def test_environment_variables_override(self, temp_config_file):
        cm = ConfigManager(temp_config_file)
        assert cm.config["host"] == "env.milvus.com"
        assert cm.config["port"] == "8888"
        assert cm.config["user"] == "envuser"
        # Config file value should still apply for non-overridden keys
        assert cm.config["password"] == "testpass"

    def test_get_method(self, config_manager):
        assert config_manager.get("host") == "test.milvus.com"
        assert config_manager.get("nonexistent_key") is None


###########################################################
# SecurityManager Tests
class TestSecurityManager:
    def test_initialization(self, security_manager, encryption_key):
        log.info(f"SecurityManager: \n {security_manager}"
                 f"Encryption Key: \n {encryption_key}")
        # assert isinstance(security_manager.cipher, Fernet)
        # assert security_manager.config is not None

    def test_encrypt_decrypt(self, security_manager):
        original_data = "sensitive information"
        encrypted = security_manager.encrypt(original_data)
        decrypted = security_manager.decrypt(encrypted)
        assert decrypted == original_data
        assert encrypted != original_data

    def test_hash_password(self, security_manager):
        password = "testpassword"
        hashed = security_manager.hash_password(password)
        assert len(hashed) == 64  # SHA256 produces 64-char hex
        assert hashed != password
        # Test consistency
        assert hashed == security_manager.hash_password(password)

    def test_authorize_admin(self, security_manager, config_manager):
        # Assuming config_manager.get("user") returns "testuser"
        assert security_manager.authorize("testuser", "read") is True
        assert security_manager.authorize("testuser", "write") is True
        assert security_manager.authorize("testuser", "any_action") is True

    def test_authorize_regular_user(self, security_manager):
        assert security_manager.authorize("otheruser", "read") is True
        assert security_manager.authorize("otheruser", "write") is True
        assert security_manager.authorize("otheruser", "admin_action") is False

    def test_encrypt_empty_string(self, security_manager):
        encrypted = security_manager.encrypt("")
        decrypted = security_manager.decrypt(encrypted)
        assert decrypted == ""

    def test_hash_empty_password(self, security_manager):
        hashed = security_manager.hash_password("")
        assert len(hashed) == 64  # SHA256 still produces 64-char hex
        assert hashed == security_manager.hash_password("")

if __name__ == "__main__":
    pytest.main()
