#!../venv/bin/python
import json
import logging
import os
import sys
from shutil import copyfile
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from .CameraController import CameraController
from .ChangeDetector import ChangeDetector
from .FileSaver import FileSaver
from .Notifier import Notifier


def create_app():
    app = FastAPI()

    # Setup logger
    app.logger = logging.getLogger('trapcam')
    app.logger.setLevel(logging.DEBUG)
    # setup logging handler for stderr
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.INFO)
    app.logger.addHandler(stderr_handler)

    # Load configuration json
    module_path = os.path.abspath(os.path.dirname(__file__))
    app.logger.info("Module path: " + module_path)
    # load central config file first
    app.user_config = json.load(open(os.path.join(module_path, "config.json")))

    # Check if a config file exists in data directory
    if os.path.isfile(os.path.join(module_path, app.user_config["data_path"], 'config.json')):
        # if yes, load that file, too
        app.logger.info("Using config file from data context")
        app.user_config = json.load(open(os.path.join(module_path,
        app.user_config["data_path"],'config.json')))
    else:
        # if not, copy central config file to data directory
        app.logger.warning("Config file does not exist within the data context, copying file")
        copyfile(os.path.join(module_path, "config.json"),
                 os.path.join(module_path, app.user_config["data_path"], "config.json"))

    # Set up logging to file
    file_handler = logging.handlers.RotatingFileHandler(os.path.join(module_path, app.user_config["data_path"], 'camera.log'), maxBytes=1024000, backupCount=5)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.info("Logging to file initialised")

    # Find photos and videos paths
    app.user_config["photos_path"] = os.path.join(module_path, app.user_config["photos_path"])
    app.logger.info("Photos path: " + app.user_config["photos_path"])
    if os.path.isdir(app .user_config["photos_path"]) is False:
        os.mkdir(app.user_config["photos_path"])
        app.logger.warning("Photos directory does not exist, creating path")
    app.user_config["videos_path"] = os.path.join(module_path, app.user_config["videos_path"])
    if os.path.isdir(app.user_config["videos_path"]) is False:
        os.mkdir(app.user_config["videos_path"])
        app.logger.warning("Videos directory does not exist, creating path")


    
    # Instantiate classes
    app.notifier = Notifier(app.user_config, app.logger)
    app.camera_controller = CameraController(app.logger, app.user_config)
    app.logger.debug("Instantiating classes ...")
    app.change_detector = ChangeDetector(app.camera_controller, app.user_config, app.logger, app.notifier)
    app.file_saver = FileSaver(app.user_config, app.logger)

    app.logger.debug("Initialisation finished")


    if app.user_config["use_ngrok"] is True:
        # pyngrok should only ever be installed or initialized in a dev environment when this flag is set
        from pyngrok import ngrok

        ngrok.set_auth_token(app.user_config["ngrok_token"])

        # Get the dev server port (defaults to 8000 for Uvicorn, can be overridden with `--port`
        # when starting the server
        port = sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else 8000

        # Open a ngrok tunnel to the dev server
        public_url = ngrok.connect(port).public_url
        app.logger.info("ngrok tunnel \"{}\" -> \"http://127.0.0.1:{}\"".format(public_url, port))

        # Update any base URLs or webhooks to use the public ngrok URL
        app.base_url = public_url
        app.notifier.notify("IDLE",public_url)
    return app

def create_error_app(e):
    # Create FastAPI app about an error occurred in the main app
    app = FastAPI()

    @app.route('/')
    def index():
        return f"<html><body><h1>Unable to start TrapCam.</h1>An error occurred:<pre>{e}</pre></body></html>"

    return app

