import json
import logging
import os
import time
import uuid
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Response
from mangum import Mangum
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

app = FastAPI(title="Cloud Items API", docs_url=None, redoc_url=None)
logger = logging.getLogger("items")
logger.setLevel(logging.INFO)
requests = Counter(
    "api_requests_total", "Requests in this execution environment", ["route", "status"]
)
latency = Histogram("api_request_seconds", "Request duration in this execution environment")


@lru_cache
def table():
    return boto3.resource(
        "dynamodb", config=Config(connect_timeout=1, read_timeout=2, retries={"max_attempts": 1})
    ).Table(os.environ["TABLE_NAME"])


@app.middleware("http")
async def observe(request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")
    elapsed = time.monotonic() - started
    requests.labels(path, str(response.status_code)).inc()
    latency.observe(elapsed)
    logger.info(
        json.dumps(
            {
                "event": "request",
                "route": path,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
            }
        )
    )
    return response


@app.get("/health")
def health():
    if os.getenv("RELEASE_HEALTH", "healthy") != "healthy":
        raise HTTPException(503, "Release readiness failed")
    try:
        # Readiness checks the actual runtime IAM permission and database path.
        table().get_item(Key={"id": "readiness-probe"})
    except (BotoCoreError, ClientError):
        raise HTTPException(503, "Storage unavailable") from None
    return {"status": "ok"}


class Item(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@app.post("/items", status_code=201)
def create_item(body: Item):
    item = {"id": str(uuid.uuid4()), "name": body.name, "expires_at": int(time.time()) + 86400}
    try:
        table().put_item(Item=item)
    except (BotoCoreError, ClientError):
        raise HTTPException(503, "Storage unavailable") from None
    return item


@app.get("/items")
def list_items():
    try:
        result = table().scan(Limit=20)
    except (BotoCoreError, ClientError):
        raise HTTPException(503, "Storage unavailable") from None
    return {"items": result.get("Items", []), "truncated": "LastEvaluatedKey" in result}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


handler = Mangum(app, lifespan="off")
