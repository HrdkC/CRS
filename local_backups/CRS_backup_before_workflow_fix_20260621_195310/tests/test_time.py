# tests/test_time.py

from datetime import datetime, timezone

print(datetime.now(timezone.utc))
print(datetime.now())