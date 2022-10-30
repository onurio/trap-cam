from threading import Thread
import io
import logging
import os
import datetime
import time
from subprocess import call
import requests

class Notifier(Thread): 

    def __init__(self, config, logger=None):
        super(Notifier, self).__init__()

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging

        self.config = config

    def notify(self, status):
        self.logger.info("Notifier: Sending notification: " + status)
        if self.config["notification"]["enabled"]:
            payload = {
                "id": self.config["notification"]["id"],
                "status": status,
            }
            try:
                # Send the notification - for now using http requests, but in the future this should be done with websockets
                requests.post(self.config["webhook_url"], json=payload)
                self.logger.info("Notifier: Notification sent")

            except:
                self.logger.error("Notifier: Error sending notification")
            

    
