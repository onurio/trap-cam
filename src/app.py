
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import time
from src.init import create_app, create_error_app

app = create_app();


try:
    app.camera_controller.start()
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
        time.sleep(0.2)

