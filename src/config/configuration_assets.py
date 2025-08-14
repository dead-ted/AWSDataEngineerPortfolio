from dataclasses import dataclass
import yaml

@dataclass
class ApplicationProps:
    account: str
    region: str
    lf_admin_role_arn: str


    def __init__(self, path:str):

        with open(path, "r") as f:
            config = yaml.safe_load(f)

        self.account = config['account']
        self.region = config['region']
        self.lf_admin_role_arn = config['lf_admin_role_arn']