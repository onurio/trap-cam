from threading import Thread
import cv2
import io
import logging
import os
import datetime
from subprocess import call
import zipfile


class FileSyncer(Thread):

    def __init__(self, config, logger=None):
        super(FileSyncer, self).__init__()

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging

        self.config = config

    def syncFile(self,file):
        # Sync a file to the cloud storage