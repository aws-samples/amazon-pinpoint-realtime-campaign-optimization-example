#!/usr/bin/env python3
import os

from aws_cdk import (
    Stack,
    App,
    Environment
)
from application.application_stack import ApplicationStack
import config as cf

app = App()
ApplicationStack(app, "ApplicationStack",
                 env=cf.CDK_ENV)

app.synth()

