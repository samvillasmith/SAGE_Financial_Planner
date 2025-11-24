#!/usr/bin/env python3
"""
Test pgvector ingest and search pipeline.
"""

import os
import sys
import json
import boto3
from dotenv import load_dotenv

# Load environment
load_dotenv(override=True)

# Verify environment
AURORA_CLUSTER_ARN = os.environ.get('AURORA_CLUSTER_ARN')
AURORA_SECRET_ARN = os.environ.get('AURORA_SECRET_ARN')
AURORA_DATABASE = os.environ.get('AURORA_DATABASE', 'sage')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT', 'sage-embedding-endpoint')
AWS_REGION = os.environ.get('DEFAULT_AWS_REGION', 'us-east-1')

if not AURORA_CLUSTER_ARN or not AURORA_SECRET_ARN:
    print("❌ Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN in environment")
    sys.exit(1)

print("🧪 Testing pgvector Pipeline")
print("=" * 50)
print(f"Region: {AWS_REGION}")
print(f"Database: {AURORA_DATABASE}")
print(f"SageMaker Endpoint: {SAGEMAKER_ENDPOINT}")
print("=" * 50)

# Initialize clients
sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=AWS_REGION)
rds_data = boto3.client('rds-data', region_name=AWS_REGION)


def get_embedding(text):
    """Get embedding from SageMaker."""
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps({'inputs': text})
    )
    result = json.loads(response['Body'].read().decode())
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]
            return result[0]
    return result


# Test 1: Check documents table exists
print("\n📋 Test 1: Checking documents table...")
try:
    result = rds_data.execute_statement(
        resourceArn=AURORA_CLUSTER_ARN,
        secretArn=AURORA_SECRET_ARN,
        database=AURORA_DATABASE,
        sql="SELECT COUNT(*) FROM documents"
    )
    count = result['records'][0][0]['longValue']
    print(f"   ✅ Documents table exists with {count} documents")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: Ingest test documents
print("\n📥 Test 2: Ingesting test documents...")
test_docs = [
    {
        "text": "Tesla reported strong Q3 earnings with record vehicle deliveries. The company's energy storage business also showed significant growth.",
        "metadata": {"source": "test", "symbol": "TSLA", "category": "earnings"}
    },
    {
        "text": "Amazon Web Services continues to dominate cloud computing market. AWS revenue grew 12% year-over-year.",
        "metadata": {"source": "test", "symbol": "AMZN", "category": "cloud"}
    },
    {
        "text": "NVIDIA's AI chips are in high demand as companies race to build AI infrastructure. GPU sales exceeded expectations.",
        "metadata": {"source": "test", "symbol": "NVDA", "category": "semiconductors"}
    }
]

import uuid
ingested_ids = []

for doc in test_docs:
    try:
        # Get embedding
        embedding = get_embedding(doc["text"])
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'

        doc_id = str(uuid.uuid4())

        # Insert into pgvector
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
                {'name': 'text', 'value': {'stringValue': doc["text"]}},
                {'name': 'embedding', 'value': {'stringValue': embedding_str}},
                {'name': 'metadata', 'value': {'stringValue': json.dumps(doc["metadata"])}}
            ]
        )

        symbol = doc["metadata"]["symbol"]
        print(f"   ✅ Ingested {symbol} document (id: {doc_id[:8]}...)")
        ingested_ids.append(doc_id)

    except Exception as e:
        print(f"   ❌ Error ingesting document: {e}")

# Test 3: Search for documents
print("\n🔍 Test 3: Searching documents...")
test_queries = [
    "electric vehicle earnings report",
    "cloud computing growth",
    "artificial intelligence chips"
]

for query in test_queries:
    try:
        # Get query embedding
        embedding = get_embedding(query)
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'

        # Search
        sql = """
            SELECT
                text,
                metadata,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM documents
            ORDER BY embedding <=> :embedding::vector
            LIMIT 1
        """

        result = rds_data.execute_statement(
            resourceArn=AURORA_CLUSTER_ARN,
            secretArn=AURORA_SECRET_ARN,
            database=AURORA_DATABASE,
            sql=sql,
            parameters=[
                {'name': 'embedding', 'value': {'stringValue': embedding_str}}
            ]
        )

        if result['records']:
            record = result['records'][0]
            text = record[0]['stringValue'][:50]
            metadata = json.loads(record[1]['stringValue'])
            # Handle different numeric types from Data API
            sim_field = record[2]
            if 'stringValue' in sim_field:
                similarity = float(sim_field['stringValue'])
            elif 'doubleValue' in sim_field:
                similarity = sim_field['doubleValue']
            else:
                similarity = 0.0
            symbol = metadata.get('symbol', 'unknown')

            print(f"   Query: '{query}'")
            print(f"   → Best match: {symbol} (similarity: {similarity:.3f})")
            print(f"   → Text: {text}...")
            print()
        else:
            print(f"   Query: '{query}' - No results")

    except Exception as e:
        print(f"   ❌ Error searching: {e}")

# Test 4: Verify count
print("📊 Test 4: Final document count...")
try:
    result = rds_data.execute_statement(
        resourceArn=AURORA_CLUSTER_ARN,
        secretArn=AURORA_SECRET_ARN,
        database=AURORA_DATABASE,
        sql="SELECT COUNT(*) FROM documents"
    )
    count = result['records'][0][0]['longValue']
    print(f"   ✅ Total documents in database: {count}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Cleanup option
print("\n" + "=" * 50)
print("🎉 pgvector pipeline test complete!")
print("\nTo clean up test documents, run:")
print("   DELETE FROM documents WHERE metadata->>'source' = 'test';")
