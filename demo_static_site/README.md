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
```