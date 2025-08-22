#!/usr/bin/env python3
import os

import aws_cdk as cdk

from src.stacks.example_stack import ExampleStack
from src.stacks.data_lake_stack import DataLakeStack
from src.stacks.etl_stack import EtlStack
from src.config.configuration_assets import ApplicationProps


app = cdk.App()

deployment_stage = app.node.try_get_context("deployment_stage")
if not deployment_stage:
    raise ValueError("Deployment requires deployment_stage value to be set in context. Value currently missing.")
configuration_path = f"configs/{deployment_stage}_config.yaml"

props = ApplicationProps(configuration_path)
aws_env = cdk.Environment(account=props.account, region=props.region)

DataLakeStack(app, "DataLakeStack", env=aws_env, props=props)

EtlStack(app, "EtlStack", env=aws_env)

ExampleStack(app, "ExampleStack", env=aws_env
    )

app.synth()
