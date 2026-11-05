from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# PostgreSQL 使用 JSONB；SQLite（本地开发/测试）退化为 JSON
JSONType = JSON().with_variant(JSONB(), "postgresql")
