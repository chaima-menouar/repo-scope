# AWS deployment path

RepoScope is container-ready. A clean portfolio-grade AWS path is:

```text
GitHub
  -> GitHub Actions
  -> Docker build
  -> Amazon ECR
  -> AWS App Runner (or ECS Fargate)
  -> RepoScope FastAPI
  -> GitHub REST API
  -> future DynamoDB snapshot store
```

## Suggested services

- **ECR** — container registry
- **App Runner** — simplest managed container deployment for the current API
- **CloudWatch** — application logs and metrics
- **Secrets Manager / App Runner secrets** — `GITHUB_TOKEN`, `OPENAI_API_KEY`
- **DynamoDB** — future durable repository snapshot/cache store
- **EventBridge Scheduler** — future scheduled re-analysis

## Container test

```bash
docker build -t repo-scope .
docker run --rm -p 8000:8000 -e GITHUB_TOKEN=... repo-scope
```

Do not bake secrets into the image. Set them in the runtime environment.
