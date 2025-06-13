import os


def get_jupyter_password_hash():
    """Retrieves the Jupyter Notebook password hash from the config file.
    """
    config_file_path = os.path.expanduser("~/.jupyter/jupyter_server_config.json")
    try:
        with open(config_file_path) as f:
            for line in f:
                if "hashed_password" in line:
                    # Extract the hashed password value
                    password_hash = line.split("p=")[1].strip().strip("'")
                    return password_hash
    except FileNotFoundError:
        return "Configuration file not found."
    return "Password hash not found in configuration file."


password_hash = get_jupyter_password_hash()
print(password_hash)

if __name__ == "__main__":
    get_jupyter_password_hash()
