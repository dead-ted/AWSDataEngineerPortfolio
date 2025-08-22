#!/usr/bin/env python3
import os

import aws_cdk as cdk

from src.config.configuration_assets import ApplicationProps
from src.stacks.static_site_stack import StaticSiteStack


app = cdk.App()

deployment_stage = app.node.try_get_context("deployment_stage")
if not deployment_stage:
    raise ValueError("Deployment requires deployment_stage value to be set in context. Value currently missing.")
configuration_path = f"configs/{deployment_stage}_config.yaml"

props = ApplicationProps(configuration_path)
aws_env = cdk.Environment(account=props.account, region=props.region)

StaticSiteStack(app, "StaticSiteStack", env=aws_env, props=props)

app.synth()
