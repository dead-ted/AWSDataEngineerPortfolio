import json
import boto3
import io
import zipfile

def lambda_handler(event, context):
    print("Event:", event)
    
    if not event.get('ResourceProperties') or event.get('RequestType') == 'Delete': 
        return {"status": "skipped"}

    bucket_name = event['ResourceProperties'].get('BucketName')
    api_url = event['ResourceProperties'].get('ApiUrl')
    
    s3 = boto3.client('s3')
    
    config_data = {
        "apiUrl": api_url
    }

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('config/config.json', json.dumps(config_data))  # add folder
    zip_buffer.seek(0)

    # Upload the zip file to S3
    s3.put_object(
        Bucket=bucket_name,
        Key="config.zip",
        Body=zip_buffer.getvalue(),  # Use the actual ZIP content
        ContentType="application/zip"
    )
    
    return {
        'PhysicalResourceId': 'ConfigWriter',
        'Data': {
            'Message': 'config.zip uploaded successfully'
        }
    }