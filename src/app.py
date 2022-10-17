
import json
from urllib import request
from fastapi import Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import time
from src.init import create_app, create_error_app

app = create_app();


try:
    app.camera_controller.start()
    app.change_detector.start()
except Exception as e:
    app = create_error_app(e)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/feed')
def feed():
    app.logger.info("Serving camera feed...")
    return StreamingResponse(generate_mjpg(app.camera_controller),200, media_type="multipart/x-mixed-replace; boundary=frame")



def generate_mjpg(camera_controller):
    while camera_controller.is_alive() is False:
        camera_controller.start()
        time.sleep(1)
    while camera_controller.is_alive():
        latest_frame = camera_controller.get_image_binary()
        response = b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + bytearray(latest_frame) + b'\r\n'
        yield(response)
        time.sleep(0.1)

@app.get('/frame')
def frame():
    app.logger.info("Requested camera frame.")
    return Response(generate_jpg(app.camera_controller),200, media_type="multipart/x-mixed-replace; boundary=frame")


def generate_jpg(camera_controller):
    """
    Generate jpg response once.
    :return: String with jpeg byte array and content type
    """
    # Start camera controller if it hasn't been started already.
    while camera_controller.is_alive() is False:
        camera_controller.start()
        time.sleep(1)
    try:
        latest_frame = camera_controller.get_image_binary()
        response = b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + bytearray(latest_frame) + b'\r\n'
        return response
    except Exception as e:
        # TODO send a error.jpg image as the frame instead.
        app.logger.warning("Could not retrieve image binary.")
        app.logger.exception(e)
        return b'Empty'
    time.sleep(0.1)


@app.get('/settings')
def get_settings():
    """
    Get current settings of the camera controller and change detector.
    :return: JSON response with settings dictionary
    """
    app.logger.info("Requested settings.")
    settings = construct_settings_object(app.camera_controller, app.change_detector)
    return settings

@app.post('/settings')
def settings_handler():
    app.logger.info("Updating settings")
    settings = request.json
    if "rotation" in settings:
        app.camera_controller.set_camera_rotation(settings["rotation"])
    if "sensitivity" in settings:
        if settings["sensitivity"] == "less":
            app.change_detector.set_sensitivity(app.user_config["less_sensitivity"],
                                                        app.user_config["max_width"])
        elif settings["sensitivity"] == "default":
            app.change_detector.set_sensitivity(app.user_config["min_width"],
                                                        app.user_config["max_width"])
        elif settings["sensitivity"] == "more":
            app.change_detector.set_sensitivity(app.user_config["more_sensitivity"],
                                                        app.user_config["max_width"])
    if "mode" in settings["exposure"]:
        if settings["exposure"]["mode"] == "auto":
            app.camera_controller.auto_exposure()
        elif settings["exposure"]["mode"] == "off":
            if settings["exposure"]["shutter_speed"] == 0:
                settings["exposure"]["shutter_speed"] = 5000
            app.camera_controller.set_exposure(settings["exposure"]["shutter_speed"],
                                                        settings["exposure"]["iso"])
    if "timelapse" in settings:
        app.logger.info("Changing timelapse settings to " + str(settings["timelapse"]))
        app.change_detector.timelapse_active = settings["timelapse"]["active"]
        app.change_detector.timelapse = settings["timelapse"]["interval"]
    
    new_settings = construct_settings_object(app.camera_controller, app.change_detector)
    return Response(json.dumps(new_settings), media_type='application/json')


def construct_settings_object(camera_controller, change_detector):
    """
    Construct a dictionary populated with the current settings of the camera controller and change detector.
    :param camera_controller: Running camera controller object
    :param change_detector: Running change detector object
    :return: settings dictionary
    """

    sensitivity = "default"
    if change_detector.minWidth == app.user_config["less_sensitivity"]:
        sensitivity = "less"
    elif change_detector.minWidth == app.user_config["min_width"]:
        sensitivity = "default"
    elif change_detector.minWidth == app.user_config["more_sensitivity"]:
        sensitivity = "more"

    settings = {
        "rotation": camera_controller.rotated_camera,
        "exposure": {
            "mode": camera_controller.get_exposure_mode(),
            "iso": camera_controller.get_iso(),
            "shutter_speed": camera_controller.get_shutter_speed(),
        },
        "sensitivity": sensitivity,
        "timelapse": {
            "active": change_detector.timelapse_active,
            "interval": change_detector.timelapse,
        }
    }
    return settings


@app.get('/session')
def get_session():
    """
    Get session status
    :return: session status json object
    """
    session_status = {
        "mode": app.change_detector.mode,
        "time_started": app.change_detector.session_start_time
    }
    return Response(json.dumps(session_status), media_type='application/json')


@app.post('/session/start')
def start_session_handler(session_type):
    """
    Start session of type photo or video
    :return: session status json object
    """
    if session_type == "photo":
        app.change_detector.start_photo_session()
    elif session_type == "video":
        app.change_detector.start_video_session()
    elif session_type == "timelapse":
        app.change_detector.start_timelapse_session()

    session_status = {
        "mode": app.change_detector.mode,
        "time_started": app.change_detector.session_start_time
    }
    return Response(json.dumps(session_status), media_type='application/json')


@app.post('/session/stop')
def stop_session_handler():
    """
    Stop running session
    :return: session status json object
    """
    app.change_detector.stop_session()
    session_status = {
        "mode": app.change_detector.mode,
        "time_started": app.change_detector.session_start_time
    }
    return Response(json.dumps(session_status), mimetype='application/json')


@app.post('/time/<time_string>')
def update_time(time_string):
    if app.change_detector.device_time is None:
        if float(time_string) > 1580317004:
            app.change_detector.device_time = float(time_string)
            app.change_detector.device_time_start = time.time()
            return Response('{"SUCCESS": "' + time_string + '"}', status=200, mimetype='application/json')
        else:
            return Response('{"ERROR": "' + time_string + '"}', status=400, mimetype='application/json')
    else:
        return Response('{"NOT_MODIFIED": "' + time_string + '"}', status=304, mimetype='application/json')
