import os
import platform
import configparser
from dotenv import load_dotenv

load_dotenv()

HOME_DIR = os.environ["USERPROFILE"] if platform.system() == "Windows" else os.environ["HOME"]

config_file_full_path = os.path.join(HOME_DIR, "dhs622.cfg")
config = configparser.ConfigParser()
config.read(config_file_full_path)

TRUTHSOCIAL_USERNAME = os.getenv("TRUTHSOCIAL_USERNAME")
TRUTHSOCIAL_PASSWORD = os.getenv("TRUTHSOCIAL_PASSWORD")
TRUTHSOCIAL_TOKEN = os.getenv("TRUTHSOCIAL_TOKEN")

api_host = "127.0.0.1"
api_port = 8000
api_base = f"http://{api_host}:{api_port}"