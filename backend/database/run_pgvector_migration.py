#!/usr/bin/env python3
"""
Run pgvector migration (002_pgvector.sql)
"""

import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Get config from environment
cluster_arn = os.environ.get("AURORA_CLUSTER_ARN")
secret_arn = os.environ.get("AURORA_SECRET_ARN")
database = os.environ.get("AURORA_DATABASE", "sage")
region = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

if not cluster_arn or not secret_arn:
    raise ValueError("Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN in environment variables")

client = boto3.client("rds-data", region_name=region)

# pgvector migration statements
statements = [
    # Enable pgvector extension
    "CREATE EXTENSION IF NOT EXISTS vector",

    # Documents table
    """CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        text TEXT NOT NULL,
        embedding vector(384),
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )""",

    # HNSW index for fast similarity search
    """CREATE INDEX IF NOT EXISTS idx_documents_embedding
    ON documents USING hnsw (embedding vector_cosine_ops)""",

    # GIN index on metadata for filtered searches
    """CREATE INDEX IF NOT EXISTS idx_documents_metadata
    ON documents USING gin (metadata)""",

    # Index on created_at
    """CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON documents (created_at DESC)""",

    # Update trigger
    """CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()""",
]

print("🚀 Running pgvector migration...")
print("=" * 50)

success_count = 0
error_count = 0

for i, stmt in enumerate(statements, 1):
    # Get a description
    stmt_type = "statement"
    if "CREATE TABLE" in stmt.upper():
        stmt_type = "table"
    elif "CREATE INDEX" in stmt.upper():
        stmt_type = "index"
    elif "CREATE TRIGGER" in stmt.upper():
        stmt_type = "trigger"
    elif "CREATE EXTENSION" in stmt.upper():
        stmt_type = "extension"

    first_line = next(l for l in stmt.split("\n") if l.strip())[:60]
    print(f"\n[{i}/{len(statements)}] Creating {stmt_type}...")
    print(f"    {first_line}...")

    try:
        response = client.execute_statement(
            resourceArn=cluster_arn, secretArn=secret_arn, database=database, sql=stmt
        )
        print(f"    ✅ Success")
        success_count += 1

    except ClientError as e:
        error_msg = e.response["Error"]["Message"]
        if "already exists" in error_msg.lower():
            print(f"    ⚠️  Already exists (skipping)")
            success_count += 1
        else:
            print(f"    ❌ Error: {error_msg}")
            error_count += 1

print("\n" + "=" * 50)
print(f"Migration complete: {success_count} successful, {error_count} errors")

if error_count == 0:
    print("\n✅ pgvector migration completed successfully!")
    print("\n📝 Your database now supports:")
    print("   - vector(384) column type")
    print("   - HNSW index for fast similarity search")
    print("   - documents table for semantic search")
else:
    print(f"\n⚠️  Some statements failed. Check errors above.")
