## About Me

In my late 20s, I made the decision to go back to school and pursue a new career path. I graduated with honors and was fortunate to start working as a data engineer on the very first day after graduation. Since then, all of my work has been focused on delivering value for the company I joined.

Now, I’m excited to build and share example projects here to showcase my skills in AWS and data engineering. These projects reflect the kinds of real-world, end-to-end solutions I’ve worked on and highlight my passion for cloud-native, scalable, and cost-effective architectures.

## Project Overview

**AWSDataEngineerPortfolio** showcases end-to-end AWS data engineering projects, including serverless ETL pipelines, DynamoDB single-table design, GIS data processing with Athena, and S3 static website hosting. All infrastructure is deployed using AWS CDK, demonstrating scalable, cost-effective, and practical cloud-native data solutions.


## CDK

The base configuration files for this project are stored in the `configs` folder at the root of the repository.

When deploying the CDK stacks, you must provide a **context variable** to specify which configuration file to use.  
Each configuration file is named using the following pattern:

<deployment_name>_conf.yaml  

The context variable name is:  
deployment_stage

### Example: Synthesizing the `dev` configuration
```bash
cdk synth -c deployment_stage=dev
