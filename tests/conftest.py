"""
The pytest_configure hook is automatically invoked by pytest
during the test session initialization. You don't need to
explicitly call it when running a test file. Instead, you
define it in a conftest.py file, and pytest will automatically
execute it before running any tests.
"""
import logging
from src.logger import getLogger as GetLogger

log = GetLogger(__name__)

# def pytest_configure(config):
#     log_file = config.getoption("--log-file", default="logs/test.log")
#
#     log.addHandler(logging.FileHandler(log_file))
#     # logging.basicConfig(
#     #     level=logging.DEBUG,
#     #     format="[%(asctime)s][%(levelname)s][%(name)s][%(lineno)s]: %(message)s",
#     #     datefmt="%Y-%m-%d %H:%M:%S",
#     #     handlers=[
#     #         logging.FileHandler(log_file),
#     #         logging.StreamHandler()
#     #     ]
#     # )