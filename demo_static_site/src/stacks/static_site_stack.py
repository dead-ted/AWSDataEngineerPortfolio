from aws_cdk import (
    Stack,
    Tags,
    Duration,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    RemovalPolicy,
    CfnOutput,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_integrations as integrations,
    aws_apigatewayv2_authorizers as authorizers,
    aws_iam as iam,
    custom_resources,
    aws_cloudformation as cfn,
    CustomResource
)
import os
from constructs import Construct
from src.config.configuration_assets import ApplicationProps

class StaticSiteStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props:ApplicationProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Apply a tag to all resources in this stack
        Tags.of(self).add("Demo", "Static Site")

        # Create an S3 bucket
        # this bucket will be used for a static s3 website
        static_site_bucket = s3.Bucket(
            self, 
            "StaticSiteBucket",
            website_index_document="index.html",
            public_read_access=True,
            removal_policy=RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                ignore_public_acls=False,
                block_public_policy=False,
                restrict_public_buckets=False
            )
        )

        stage_bucket = s3.Bucket(
            self, 
            "StaticSiteStageBucket",
            public_read_access=False,
            removal_policy=RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=True,
                ignore_public_acls=True,
                block_public_policy=True,
                restrict_public_buckets=True
            )
        )

        # Create an HTTP API Gateway
        http_api = apigatewayv2.HttpApi(
            self,
            "StaticSiteBackendHTTPAPI",
            api_name="staticSiteBackendHTTPAPI",
            description="This is the backend for the static site using HTTP API Gateway.",
            cors_preflight=apigatewayv2.CorsPreflightOptions(
            allow_headers=[
                "*"
            ],
            allow_methods=[apigatewayv2.CorsHttpMethod.GET, apigatewayv2.CorsHttpMethod.OPTIONS, apigatewayv2.CorsHttpMethod.POST
            ],
            allow_origins=[static_site_bucket.bucket_website_url],
            max_age=Duration.days(10)
            )
        )

        blog_post_dynamodb_table = dynamodb.Table(
            self,
            "StaticSiteBlogPostsTable",
            partition_key=dynamodb.Attribute(
                name="post_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.RETAIN,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # lambda_auth_role = iam.Role(
        #     self,
        #     "StaticSiteLambdaAuthRole",
        #     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        # )

        # lambda_auth_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))

        # Lambda authorizer
        # auth_handler_code_location = os.path.join(os.getcwd(), "src/assets/lambdas/lambda-auth")
        # auth_handler = lambda_.Function(
        #     self, 'StaticSiteAuthLambda',
        #     runtime=lambda_.Runtime.PYTHON_3_10,
        #     handler='lambda_function.lambda_handler',
        #     code=lambda_.Code.from_asset(auth_handler_code_location),
        #     role=lambda_auth_role,
        #     timeout=Duration.seconds(30)
        # )

        # authorizer = authorizers.HttpLambdaAuthorizer("SimpleAuthorizer", auth_handler,
        #     response_types=[authorizers.HttpLambdaResponseType.SIMPLE]
        # )

        api_code_location = os.path.join(os.getcwd(), "src/assets/lambdas/lambda-api")
        lambda_api = lambda_.Function(
            self,
            "StaticSiteLambdaAPI",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(api_code_location),
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, 
                    "StaticSitePowertoolsLayer",
                    f"arn:aws:lambda:{props.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:78"
                )
            ],
            environment={
                "DDB_TABLE_NAME": blog_post_dynamodb_table.table_name,
                "STATIC_SITE_URL": static_site_bucket.bucket_website_url
            },
            timeout=Duration.seconds(30),
            tracing=lambda_.Tracing.ACTIVE
        )

        blog_post_dynamodb_table.grant_read_write_data(lambda_api)

        lambda_integration = integrations.HttpLambdaIntegration(
            "StaticSiteLambdaIntegration",
            handler=lambda_api
        )

        http_api.add_routes(
            path="/get_posts",
            methods=[apigatewayv2.HttpMethod.GET],
            integration=lambda_integration,
            # authorizer=authorizer
        )

        http_api.add_routes(
            path="/add_post",
            methods=[apigatewayv2.HttpMethod.POST],
            integration=lambda_integration,
            # authorizer=authorizer
        )

        #lambda function role
        lambda_dynamic_config_creator_role = iam.Role(
            self,
            "StaticSiteLambdaDynamicConfigCreatorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_dynamic_config_creator_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))

        dynamic_config_creator_code_location = os.path.join(os.getcwd(), "src/assets/lambdas/website-dynamic-config-builder")
        lambda_dynamic_config_creator = lambda_.Function(
            self, 'StaticSiteDynamicConfigCreatorLambda',
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler='lambda_function.lambda_handler',
            code=lambda_.Code.from_asset(dynamic_config_creator_code_location),
            role=lambda_dynamic_config_creator_role,
            timeout=Duration.seconds(30),
        )

        stage_bucket.grant_read_write(lambda_dynamic_config_creator)

        # Create Custom Resource
        provider = custom_resources.Provider(
            self,
            "StaticSiteConfigCustomResourceProvider",
            on_event_handler=lambda_dynamic_config_creator
        )

        dynamic_config_custom_resource_lambda = CustomResource(self, "StaticSiteDynamicConfigCustomResource",
            service_token=provider.service_token,
            properties={
                "ApiUrl": http_api.api_endpoint,
                "BucketName": stage_bucket.bucket_name,
                "dynamic_config_zip_key": props.dynamic_config_zip_key
            }
        )

        website_content_path = os.path.join(os.getcwd(), "src/assets/website-content")
        website_deployment = s3_deployment.BucketDeployment(
            self, 
            "StaticSiteDeployWebsite",
            sources=[s3_deployment.Source.asset(website_content_path)],
            destination_bucket=static_site_bucket,
            prune=False
        )

        dynamic_config_deployment = s3_deployment.BucketDeployment(
            self,
            "StaticSiteDeployConfig",
            sources=[s3_deployment.Source.bucket(stage_bucket, props.dynamic_config_zip_key)],
            destination_bucket=static_site_bucket,
            prune=False
        )

        dynamic_config_deployment.node.add_dependency(dynamic_config_custom_resource_lambda)

        # Output the website URL
        CfnOutput(
            self, 
            "BucketWebsiteURL",
            value=static_site_bucket.bucket_website_url,
            description="URL of the static website"
        )

        #cfn output for the api gateway
        CfnOutput(
            self,
            "HTTPAPIGatewayURL",
            value=http_api.api_endpoint,
            description="URL of the HTTP API Gateway"
        )