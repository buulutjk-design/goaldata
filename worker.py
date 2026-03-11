# worker.py
import os
import json
import redis
from celery import Celery
from analysis import evaluate_match
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("banko-worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

celery = Celery("banko", broker=CELERY_BROKER, backend=CELERY_BACKEND)

@celery.task(bind=True, max_retries=3, soft_time_limit=300)
def process_batch(self, batch_size=2000):
    try:
        items = []
        for _ in range(batch_size):
            raw = r.rpop("requests_queue")
            if not raw:
                break
            try:
                items.append(json.loads(raw))
            except Exception:
                continue
        if not items:
            return {"processed": 0}
        best = None
        for it in items:
            res = evaluate_match(it, n_sim=3000)
            if not res:
                continue
            if not best or res["confidence"] > best["confidence"]:
                best = res
        r.rpush("analysis_logs", json.dumps({"time": __import__("datetime").datetime.utcnow().isoformat(), "processed": len(items), "best": best}))
        return {"processed": len(items), "best": best}
    except Exception as exc:
        logger.exception("process_batch failed")
        raise self.retry(exc=exc, countdown=10)
