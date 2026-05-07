# INFRASTRUCTURE
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_PATH = Path(__file__).parent.parent.parent / "src" / "logs" / "query_log.jsonl"


# FUNCTIONS

# Append one JSONL record per query; fail-soft on any write error
def log_query(record: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("query_log write failed: %s", e)
