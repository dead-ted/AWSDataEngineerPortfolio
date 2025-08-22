import pytest
from typing import Any, Dict
import lambda_tdd_v2
import os
import json
import boto3
from dataclasses import dataclass, asdict
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext as LambdaContextData

@dataclass
class LambdaContext:
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

@pytest.fixture
def mock_context():
    return LambdaContext()

@pytest.fixture
def set_up_local_env():
    endpoint_url = "http://localhost:8000"
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=endpoint_url
    )
    table_name = 'blogPostsTable'
    try:
        #create a dynamodb table with with the table test_table 
        key_schema = [
            {
                'AttributeName': 'post_id',
                'KeyType': 'HASH' 
            }
        ]
        attribute_definitions = [
            {
                'AttributeName': 'post_id',
                'AttributeType': 'S'
            }
        ]
        provisioned_throughput = {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput=provisioned_throughput
        )
        print('create table complete!')
    except Exception as e:
        print(e)

    try:
        response = dynamodb.batch_write_item(
            RequestItems={
                table_name: [
                    {
                        'PutRequest': {
                            'Item': {
                                'post_id': '1',
                                'title': 'First Post',
                                'content': 'This is the first post'
                            }
                        }
                    },
                    {
                        'PutRequest': {
                            'Item': {
                                'post_id': '2',
                                'title': 'Second Post',
                                'content': 'This is the second post'
                            }
                        }
                    },
                    {
                        'PutRequest': {
                            'Item': {
                                'post_id': '3',
                                'title': 'Third Post',
                                'content': 'This is the third post'
                            }
                        }
                    }
                ]
            }
        )
        print('UnprocessedItems :')
        print(response.get('UnprocessedItems', {}))
    
        print('add records complete!')
    except Exception as e:
        print(e)

@pytest.fixture
def post_object():
    return lambda_tdd_v2.Blog_post("333333", "test_title", "test_content")

@pytest.fixture
def api_gateway_event_add_post():
    return {
        "version": "2.0",
        "routeKey": "POST /add_post",
        "rawPath": "/add_post",
        "rawQueryString": "context=blog&title=NewPost",
        "queryStringParameters": {
            "content": "blog",
            "title": "NewPost"
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
                "method": "POST",
                "path": "/add_post",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "PostmanRuntime/7.28.0"
            },
            "requestId": "id",
            "routeKey": "POST /add_post",
            "stage": "$default",
            "time": "12/Mar/2021:19:03:58 +0000",
            "timeEpoch": 1615577038397
        },
        "body": '{"title": "New Post", "content": "This is the content of the new post."}',
        "isBase64Encoded": False
    }

@pytest.fixture
def api_gateway_event_get_posts():
    return {
        "version": "2.0",
        "routeKey": "GET /get_posts",
        "rawPath": "/get_posts",
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

# UNIT TESTS
def test_create_post_input():
    create_post_res = lambda_tdd_v2.create_post("test_title", "test_content") 
    assert create_post_res.title == "test_title"
    assert create_post_res.content == "test_content"
    assert create_post_res.post_id is not None
    isinstance(create_post_res.post_id, str)
    assert isinstance(create_post_res, lambda_tdd_v2.Blog_post)

def test_create_post_error():
    with pytest.raises(Exception, match="Content issue."):
        lambda_tdd_v2.create_post("test_title", "")

    with pytest.raises(Exception, match="Title issue."):
        lambda_tdd_v2.create_post("", "test_content")

def test_create_post_length():
    # the title and posts should have a limited amount of characters in the end resulting objects
    # the length of the title should be 100 characters
    # the length of the content should be 2000 characters
    long_string = "a" * 3500

    create_post_res_1 = lambda_tdd_v2.create_post("test_title", long_string)
    assert len(create_post_res_1.content) == 2000

    create_post_res_2 = lambda_tdd_v2.create_post(long_string, "test_content")
    assert len(create_post_res_2.title) == 100

# INTEGRATION TESTS
def test_put_row(set_up_local_env, post_object):
    set_up_local_env

    assert lambda_tdd_v2.put_row(asdict(post_object), os.environ["DDB_TABLE_NAME"])
    
def test_fetch_posts(set_up_local_env, post_object):
    set_up_local_env

    res_posts = lambda_tdd_v2.fetch_posts(os.environ['DDB_TABLE_NAME'])
    isinstance(res_posts, list)
    for i in res_posts:
        assert isinstance(i, lambda_tdd_v2.Blog_post)

def test_fetch_posts(set_up_local_env, post_object):
    set_up_local_env

    res_posts = lambda_tdd_v2.fetch_posts(os.environ['DDB_TABLE_NAME'])
    isinstance(res_posts, list)
    for i in res_posts:
        assert isinstance(i, lambda_tdd_v2.Blog_post)

def test_add_post(api_gateway_event_get_posts, mock_context):
    res_get_posts = lambda_tdd_v2.lambda_handler(api_gateway_event_get_posts, mock_context)['body']
    assert isinstance(res_get_posts, str)
    body = json.loads(res_get_posts)
    assert isinstance(body, list)
    for i in body:
        assert isinstance(i, dict)
        assert "post_id" in i
        assert "title" in i
        assert "content" in i