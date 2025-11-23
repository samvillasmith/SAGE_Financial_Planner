# SAGE Terraform Infrastructure

Infrastructure as Code for the SAGE (Strategic Agentic Generative Explainer) financial planning platform.

## Architecture Overview

SAGE uses a modular Terraform structure with independent directories for each service layer:

- **`2_sagemaker/`** - SageMaker serverless endpoint for text embeddings
- **`3_ingestion/`** - S3 Vectors, Lambda, and API Gateway for document ingestion
- **`4_researcher/`** - App Runner service for autonomous research agent
- **`5_database/`** - Aurora Serverless v2 PostgreSQL with Data API
- **`6_agents/`** - Lambda functions for multi-agent orchestration
- **`7_frontend/`** - CloudFront, S3, and API Gateway for frontend
- **`8_enterprise/`** - CloudWatch dashboards and monitoring

## Design Principles

### Independent Deployment

Each directory maintains its own state file, enabling:
- Incremental deployment and testing
- Isolated failure domains
- Independent scaling decisions

### Local State

State files are stored locally for simplicity:
- No S3 backend configuration required
- Zero additional infrastructure costs
- All `*.tfstate` files are gitignored

## Usage

```bash
# Navigate to service directory
cd terraform/4_researcher

# Initialize (first time only)
terraform init

# Preview changes
terraform plan

# Deploy
terraform apply

# Cleanup
terraform destroy
```

## Environment Variables

Required variables (stored in root `.env`):

| Variable | Source | Description |
|----------|--------|-------------|
| `OPENAI_API_KEY` | OpenAI | API key for models |
| `SAGE_API_ENDPOINT` | Part 3 output | Ingestion API Gateway URL |
| `SAGE_API_KEY` | Part 3 output | API Gateway key |
| `AURORA_CLUSTER_ARN` | Part 5 output | Database cluster ARN |
| `AURORA_SECRET_ARN` | Part 5 output | Database credentials |
| `VECTOR_BUCKET` | Part 3 output | S3 Vectors bucket name |

## Production Considerations

For production deployments, consider:
- **Remote State**: S3 backend with DynamoDB locking
- **Modules**: Reusable configurations across environments
- **Workspaces**: Multi-environment management (dev/staging/prod)
- **CI/CD**: Automated deployment pipelines

## Troubleshooting

**State Conflicts**: Import existing resources
```bash
terraform import <resource_type>.<resource_name> <resource_id>
```

**Clean Slate**: Reset a directory
```bash
terraform destroy
rm -rf .terraform terraform.tfstate*
terraform init
```

---

## Acknowledgments

This project architecture is inspired by [Ed Donner's](https://github.com/ed-donner) "AI in Production" course. Thank you Ed for the excellent foundation and teaching approach that made this possible.

---

*Built by Samuel Villa-Smith*
