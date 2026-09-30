from app.backend.db.base import BaseDatabase
from app.backend.db.mock_db import MockDatabase

# Local / Testing: MockDatabase instance
# Production: Swap to S3ParquetDatabase() or PostgresDatabase()
_db_instance: BaseDatabase = MockDatabase()


def get_db() -> BaseDatabase:
    return _db_instance
