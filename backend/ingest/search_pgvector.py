"""
Search function for Aurora pgvector.
Replaces S3 Vectors query_vectors with PostgreSQL similarity search.
"""

import json
import os
import boto3

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


def search_documents(query_text, k=5, metadata_filter=None):
    """
    Search documents using pgvector similarity search.

    Args:
        query_text: Text to search for
        k: Number of results to return
        metadata_filter: Optional dict for filtering (e.g., {"symbol": "AAPL"})

    Returns:
        List of results with id, text, score, and metadata
    """
    # Get embedding for query
    print(f"Getting embedding for query: {query_text}")
    query_embedding = get_embedding(query_text)

    # Format embedding as PostgreSQL vector string
    embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

    # Build SQL query with cosine distance
    # <=> is the cosine distance operator (lower is more similar)
    sql = """
        SELECT
            id::text,
            text,
            1 - (embedding <=> :embedding::vector) as similarity,
            metadata
        FROM documents
    """

    parameters = [
        {'name': 'embedding', 'value': {'stringValue': embedding_str}},
        {'name': 'k', 'value': {'longValue': k}}
    ]

    # Add metadata filter if provided
    if metadata_filter:
        conditions = []
        for i, (key, value) in enumerate(metadata_filter.items()):
            param_name = f'filter_{i}'
            conditions.append(f"metadata->>'{key}' = :{param_name}")
            parameters.append({'name': param_name, 'value': {'stringValue': str(value)}})

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

    sql += """
        ORDER BY embedding <=> :embedding::vector
        LIMIT :k
    """

    print(f"Searching in Aurora pgvector...")
    response = rds_data.execute_statement(
        resourceArn=AURORA_CLUSTER_ARN,
        secretArn=AURORA_SECRET_ARN,
        database=AURORA_DATABASE,
        sql=sql,
        parameters=parameters
    )

    # Format results
    results = []
    for record in response.get('records', []):
        doc_id = record[0]['stringValue']
        text = record[1]['stringValue']
        # Handle different numeric types from Data API
        sim_field = record[2]
        if 'stringValue' in sim_field:
            similarity = float(sim_field['stringValue'])
        elif 'doubleValue' in sim_field:
            similarity = sim_field['doubleValue']
        else:
            similarity = 0.0
        metadata = json.loads(record[3]['stringValue'])

        results.append({
            'id': doc_id,
            'text': text,
            'score': similarity,
            'metadata': metadata
        })

    return results


def lambda_handler(event, context):
    """
    Search handler for Lambda.
    Expects JSON body with:
    {
        "query": "Search query text",
        "k": 5,  # Optional, defaults to 5
        "filter": {"symbol": "AAPL"}  # Optional metadata filter
    }
    """
    # Parse the request body
    if isinstance(event.get('body'), str):
        body = json.loads(event['body'])
    else:
        body = event.get('body', event)

    query_text = body.get('query')
    k = body.get('k', 5)
    metadata_filter = body.get('filter')

    if not query_text:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: query'})
        }

    results = search_documents(query_text, k, metadata_filter)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'results': results,
            'count': len(results)
        })
    }


# For local testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Reload environment after dotenv
    AURORA_CLUSTER_ARN = os.environ.get('AURORA_CLUSTER_ARN')
    AURORA_SECRET_ARN = os.environ.get('AURORA_SECRET_ARN')
    SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')

    # Reinitialize clients with correct region
    AWS_REGION = os.environ.get('DEFAULT_AWS_REGION', 'us-east-1')
    sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=AWS_REGION)
    rds_data = boto3.client('rds-data', region_name=AWS_REGION)

    # Test search
    results = search_documents("technology earnings report", k=3)

    print(f"\nFound {len(results)} results:")
    for r in results:
        print(f"\n  Score: {r['score']:.3f}")
        print(f"  Text: {r['text'][:100]}...")
        print(f"  Metadata: {r['metadata']}")
