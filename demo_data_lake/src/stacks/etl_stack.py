from aws_cdk import (
    Duration,
    Stack,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    Fn
)
from constructs import Construct
import os


class EtlStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        landing_bucket_name = Fn.import_value("LandingBucketName")
        landing_bucket = s3.Bucket.from_bucket_name(self, "LandingBucketRef", landing_bucket_name)


        # Population Scraper Dockerfile directory
        docker_image_path = os.path.join(os.getcwd(), "src/assets/lambdas/population_scraper")

        # Population Scraper Lambda Function
        population_scraper_lambda = _lambda.DockerImageFunction(
            self,
            "PopulationScraperLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                directory=docker_image_path
            ),
            memory_size=3008,
            timeout=Duration.seconds(300),
            environment = {
                "S3_BUCKET": landing_bucket_name,
                "S3_PATH": "population_scrape/california/",
                "CHROME_BINARY": "/opt/chrome/chrome",
                "CHROME_DRIVER": "/opt/chromedriver",
                "DATA_URL": "https://worldpopulationreview.com/us-cities/california"
            }
        )

        landing_bucket.grant_put(population_scraper_lambda)

        rule = events.Rule(
            self, "PopulationScraperMidnightPSTRule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="8",
            )
        )

        rule.add_target(targets.LambdaFunction(population_scraper_lambda))


