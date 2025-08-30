from dataclasses import dataclass, asdict
import uuid
import os
import boto3
import json
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver

logger = Logger(service="APP")
tracer = Tracer(service="APP")

ddb_table_name = os.environ["DDB_TABLE_NAME"]
static_site_url = os.environ["STATIC_SITE_URL"]
user_message_sns_arn = os.environ["USER_MESSAGE_SNS_ARN"]

app = APIGatewayHttpResolver()

if os.environ.get('LOCAL') == 'true':
    endpoint_url = "http://localhost:8000"

    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=endpoint_url
    )
else:
    dynamodb = boto3.resource(
        'dynamodb'
    )

sns = boto3.client('sns')

@dataclass
class Blog_post:
    post_id: str
    title: str
    content: str

def create_post(title:str, content:str, post_id:str = None) -> Blog_post:
    if not post_id:
        post_id = str(uuid.uuid4())

    try:
        title = str(title)
        title = title.strip()
        if not title:
            raise ValueError("Title cannot be empty.")
        if len(title) > 100:
            title = title[:100]
    except Exception as e:
        raise Exception(f'Title issue.')

    try:
        content = str(content)
        content = content.strip()
        if not content:
            raise ValueError("Content cannot be empty.")
        if len(content) > 2000:
            content = content[:2000]
    except Exception as e:
        raise Exception(f'Content issue.')

    return Blog_post(
        post_id=post_id,
        title=title,
        content=content
    )

def put_row(new_row: Dict[str, str], ddb_tn: str) -> str:
    table = dynamodb.Table(ddb_tn)
    response = table.put_item(
        Item=new_row
    )

    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception("Error adding row")

    return True

def fetch_posts(ddb_tn:str) -> list[Blog_post]:
    # get all items from dynamodb
    try:
        table = dynamodb.Table(ddb_tn)
        res_scan = table.scan()
    except ClientError as e:
        error_code = e.response['Error']['Code']

        if error_code == 'ResourceNotFoundException':
            raise Exception("Table not found")
        
    # convert all items to blog post objects
    processed_posts = []
    for post in res_scan['Items']: 
        try:
            required_keys = ['post_id', 'title', 'content']
            if all(item in required_keys for item in post.keys()):
                key_filter_dict = {key: post[key] for key in required_keys if key in post}
                processed_posts.append(Blog_post(**post))
            else:
                raise ValueError("Missing required keys in post")
        except Exception as e:
            logger.error(f"Error processing post: {e}. post -> {post}")
    
    return processed_posts

@app.post("/add_post")
@tracer.capture_method
def add_post() -> Dict[str, str]:
    tracer.put_annotation(key="User", value=str(app.current_event.json_body)) #value is a param
    logger.info(f"Request for creating post received.")

    new_title = app.current_event.json_body.get('title', None)
    new_content = app.current_event.json_body.get('content', None)
    if not new_title or not new_content:
        return {"Error": "Title and content are required."}

    new_post = create_post(new_title, new_content)

    if put_row(asdict(new_post), ddb_table_name):
        return {"Message": "Row added to table."}
    else:
        return {"Error: Failed to add row."}
    
@app.get("/get_posts")
@tracer.capture_method
def get_posts() -> list[Dict[str, str]]:
    tracer.put_annotation(key="User", value='')
    logger.info(f"Request for table data received")

    # scan dynamodb
    query_res = fetch_posts(os.environ['DDB_TABLE_NAME'])
    logger.info(f"Data extracted from dynamodb")
    
    # return rows extracted from response
    extracted_rows = [asdict(post) for post in query_res]
    logger.info(f"found {len(extracted_rows)} rows to display.")
    
    return extracted_rows

@app.post("/send_message")
@tracer.capture_method
def send_message() -> Dict[str, str]:
    tracer.put_annotation(key="User", value='')
    logger.info(f"Sending message to sns for delivery")

    print(app.current_event.json_body)

    try:
        message = {
            "name": app.current_event.json_body.get('yourName', None),
            "subject": app.current_event.json_body.get('subject', None),
            "message": app.current_event.json_body.get('message', None),
        }

        response = sns.publish(
            TopicArn=user_message_sns_arn,
            Message=json.dumps(message),  # Convert dict to JSON string
            Subject=f"New user message from {app.current_event.json_body.get('yourName', None)}"
        )
    
        return {"status": "success", "message": "Message sent successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext):
    logger.info(event)
    res = app.resolve(event, context)

    return res

if __name__ == '__main__':
    class FakeLambdaContext:
        function_name: str = "my_lambda_function"
        function_version: str = "$LATEST"
        invoked_function_arn: str = "arn:aws:lambda:us-east-1:123456789012:function:my_lambda_function"
        memory_limit_in_mb: int = 128
        aws_request_id: str = "1234-5678-9012"
        log_group_name: str = "/aws/lambda/my_lambda_function"
        log_stream_name: str = "2023/09/01/[$LATEST]1234567890abcdef"
        identity: dict = None
        client_context: dict = None
        remaining_time_in_millis: int = 3000

    event = {
        "version": "2.0",
        "routeKey": "GET /send_message",
        "rawPath": "/send_message",
        "rawQueryString": "context=blog&title=NewPost",
        "queryStringParameters": {
        },
        "headers": {
            "accept": "*/*",
            "content-type": "application/json",
            "host": "localhost",
            "user-agent": "PostmanRuntime/7.28.0",
            "x-amzn-trace-id": "Root=1-60c9ab01-2c5b3f7e4b3e2a95d67fda38",
            "x-forwarded-for": "127.0.0.1",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https"
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "domainName": "localhost",
            "domainPrefix": "api",
            "http": {
                "method": "GET",
                "path": "/get_posts",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "PostmanRuntime/7.28.0"
            },
            "requestId": "id",
            "routeKey": "GET /get_posts",
            "stage": "$default",
            "time": "12/Mar/2021:19:03:58 +0000",
            "timeEpoch": 1615577038397
        },
        "body": '',
        "isBase64Encoded": False
    }
