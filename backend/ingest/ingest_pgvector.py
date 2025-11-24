"""
Lambda function for ingesting text into Aurora pgvector with embeddings.
Replaces S3 Vectors with PostgreSQL pgvector for semantic search.
"""

import json
import os
import boto3
import datetime
import uuid

# Environment variables
AURORA_CLUSTER_ARN = os.environ.get('AURORA_CLUSTER_ARN')
AURORA_SECRET_ARN = os.environ.get('AURORA_SECRET_ARN')
AURORA_DATABASE = os.environ.get('AURORA_DATABASE', 'sage')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')
AWS_REGION = os.environ.get('DEFAULT_AWS_REGION', 'us-east-1')

# Initialize AWS clients
sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=AWS_REGION)
rds_data = boto3.client('rds-data', region_name=AWS_REGION)


def get_embedding(text):
    """Get embedding vector from SageMaker endpoint."""
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps({'inputs': text})
    )

    result = json.loads(response['Body'].read().decode())
    # HuggingFace returns nested array [[[embedding]]], extract the actual embedding
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]  # Extract from [[[embedding]]]
            return result[0]  # Extract from [[embedding]]
    return result  # Return as-is if not nested


def lambda_handler(event, context):
    """
    Main Lambda handler.
    Expects JSON body with:
    {
        "text": "Text to ingest",
        "metadata": {
            "source": "optional source",
            "category": "optional category",
            "symbol": "optional symbol"
        }
    }
    """
    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)

        text = body.get('text')
        metadata = body.get('metadata', {})

        if not text:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required field: text'})
            }

        # Get embedding from SageMaker
        print(f"Getting embedding for text: {text[:100]}...")
        embedding = get_embedding(text)

        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())

        # Format embedding as PostgreSQL vector string
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'

        # Add timestamp to metadata
        metadata['timestamp'] = datetime.datetime.utcnow().isoformat()

        # Store in Aurora with pgvector
        print(f"Storing document in Aurora pgvector...")

        sql = """
            INSERT INTO documents (id, text, embedding, metadata)
            VALUES (:id::uuid, :text, :embedding::vector, :metadata::jsonb)
        """

        rds_data.execute_statement(
            resourceArn=AURORA_CLUSTER_ARN,
            secretArn=AURORA_SECRET_ARN,
            database=AURORA_DATABASE,
            sql=sql,
            parameters=[
                {'name': 'id', 'value': {'stringValue': doc_id}},
                {'name': 'text', 'value': {'stringValue': text}},
                {'name': 'embedding', 'value': {'stringValue': embedding_str}},
                {'name': 'metadata', 'value': {'stringValue': json.dumps(metadata)}}
            ]
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document indexed successfully',
                'document_id': doc_id
            })
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# For local testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Reload environment after dotenv
    AURORA_CLUSTER_ARN = os.environ.get('AURORA_CLUSTER_ARN')
    AURORA_SECRET_ARN = os.environ.get('AURORA_SECRET_ARN')
    SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')

    test_event = {
        'text': 'Apple Inc reported strong quarterly earnings driven by iPhone sales.',
        'metadata': {
            'source': 'test',
            'category': 'earnings',
            'symbol': 'AAPL'
        }
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
