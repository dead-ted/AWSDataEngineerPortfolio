from aws_cdk import (
    Duration,
    Stack,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_lakeformation as lf,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
from src.config.configuration_assets import ApplicationProps

class DataLakeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props:ApplicationProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        landing_bucket = s3.Bucket(
            self, "LandingBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        processed_bucket = s3.Bucket(
            self, "ProcessedBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        published_bucket = s3.Bucket(
            self, "PublishedBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        CfnOutput(self, "LandingBucketName", value=landing_bucket.bucket_name)
        CfnOutput(self, "ProcessedBucketName", value=processed_bucket.bucket_name)
        CfnOutput(self, "PublishedBucketName", value=published_bucket.bucket_name)

        lf_admin_role = iam.Role(
            self, "LFAdminRole",
            assumed_by=iam.ArnPrincipal(props.lf_admin_role_arn),
            role_name=f"LFAdminRole-{self.account}-{self.region}",
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")]
        )

        
        lf.CfnDataLakeSettings(
            self,
            "DataLakeSettings",
            admins=[
                lf.CfnDataLakeSettings.DataLakePrincipalProperty(
                    data_lake_principal_identifier=lf_admin_role.role_arn
                )
            ]
        )     

        # for bucket in [processed_bucket, published_bucket]:
        #     lf.CfnResource(
        #         self, f"LFResource{bucket.node.id}",
        #         resource_type="DATA_LOCATION",
        #         resource_arn=bucket.bucket_arn,
        #         role_arn=props.lf_admin_role_arn
        #     )