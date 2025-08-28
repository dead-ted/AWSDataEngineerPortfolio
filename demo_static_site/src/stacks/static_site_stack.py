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
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                ignore_public_acls=False,
                block_public_policy=False,
                restrict_public_buckets=False
            )
        )

        stage_bucket = s3.Bucket(
            self, 
            "StageBucket",
            public_read_access=False,
            removal_policy=RemovalPolicy.DESTROY,
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




        #create a dynamodb table for storing blog posts
        blog_post_dynamodb_table = dynamodb.Table(
            self,
            "BlogPostsTable",
            partition_key=dynamodb.Attribute(
                name="post_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        #lambda function role
        lambda_auth_role = iam.Role(
            self,
            "LambdaAuthRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_auth_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))

        # Define your Lambda authorizer
        auth_handler_code_location = os.path.join(os.getcwd(), "src/assets/lambdas/lambda-auth")
        auth_handler = lambda_.Function(
            self, 'AuthLambda',
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler='lambda_function.lambda_handler',
            code=lambda_.Code.from_asset(auth_handler_code_location),
            role=lambda_auth_role,
            timeout=Duration.seconds(30)
        )

        authorizer = authorizers.HttpLambdaAuthorizer("SimpleAuthorizer", auth_handler,
            response_types=[authorizers.HttpLambdaResponseType.SIMPLE]
        )



        api_code_location = os.path.join(os.getcwd(), "src/assets/lambdas/lambda-api")
        lambda_api = lambda_.Function(
            self,
            "LambdaAPI",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="lambda_tdd_v2.lambda_handler",
            code=lambda_.Code.from_asset(api_code_location),
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, 
                    "PowertoolsLayer",
                    "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:78"  # Replace with the correct ARN
                )
            ],
            environment={
                "DDB_TABLE_NAME": blog_post_dynamodb_table.table_name,
                "ENDPOINT": http_api.api_endpoint,
                "STATIC_SITE_URL": static_site_bucket.bucket_website_url
            },
            timeout=Duration.seconds(30),
            tracing=lambda_.Tracing.ACTIVE
        )

        blog_post_dynamodb_table.grant_read_write_data(lambda_api)

        # Lambda integration
        lambda_integration = integrations.HttpLambdaIntegration(
            "LambdaIntegration",
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
        lambda_website_creator_role = iam.Role(
            self,
            "LambdaWebsiteCreatorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_website_creator_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))


        website_creator_code_location = os.path.join(os.getcwd(), "src/assets/lambdas/website_creator")
        lambda_website_creator_handler = lambda_.Function(
            self, 'websiteCreatorLambda',
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler='lambda_function.lambda_handler',
            code=lambda_.Code.from_asset(website_creator_code_location),
            role=lambda_website_creator_role,
            timeout=Duration.seconds(30),
        )

        stage_bucket.grant_read_write(lambda_website_creator_handler)

        # Create Custom Resource
        provider = custom_resources.Provider(
            self,
            "ConfigCustomResourceProvider",
            on_event_handler=lambda_website_creator_handler
        )

        custom_resource_lambda = CustomResource(self, "my-cr",
            service_token=provider.service_token,
            properties={
                "ApiUrl": http_api.api_endpoint,
                "BucketName": stage_bucket.bucket_name,
                "OtherProperty": "value"
            }
        )

        # Deploy static website content to the bucket
        website_content_path = os.path.join(os.getcwd(), "src/assets/website-content")
        s3_deployment.BucketDeployment(
            self, 
            "DeployWebsite",
            sources=[s3_deployment.Source.asset(website_content_path)],
            destination_bucket=static_site_bucket,
            prune=False
        )

        # Deploy static website content to the bucket
        deployment = s3_deployment.BucketDeployment(
            self, 
            "DeployConfig",
            sources=[s3_deployment.Source.bucket(stage_bucket, "config.zip")],
            destination_bucket=static_site_bucket,
            prune=False
        )

        deployment.node.add_dependency(custom_resource_lambda)

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