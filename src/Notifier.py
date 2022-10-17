from threading import Thread
import io
import logging
import os
import datetime
from subprocess import call

class Notifier(Thread):

    def __init__(self, config, logger=None):
        super(Notifier, self).__init__()

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging

        self.config = config

    def notify(self,metadata,message):
        # Notify subscribers.

    
