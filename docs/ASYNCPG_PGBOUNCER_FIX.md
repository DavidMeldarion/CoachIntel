# SQLAlchemy + AsyncPG + PgBouncer/Supabase Connection Pooling Fix

## The Problem

When using SQLAlchemy with asyncpg and connection poolers (like Supabase's PgBouncer), you may encounter:

```
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: 
<class 'asyncpg.exceptions.DuplicatePreparedStatementError'>: 
prepared statement "__asyncpg_stmt_X__" already exists
```

## Root Cause

- **Prepared Statements**: AsyncPG creates prepared statements to optimize repeated queries
- **Connection Pooling**: PgBouncer in "transaction" mode doesn't properly handle prepared statements
- **Conflict**: When connections are reused, prepared statements clash

## The Solution (Applied in models.py)

### Method 1: URL Parameters + NullPool
```python
# Add parameters to database URL
if "?" in ASYNC_DATABASE_URL:
    ASYNC_DATABASE_URL += "&prepared_statement_cache_size=0&statement_cache_size=0"
else:
    ASYNC_DATABASE_URL += "?prepared_statement_cache_size=0&statement_cache_size=0"

# Configure engine
engine = create_async_engine(
    ASYNC_DATABASE_URL, 
    echo=True, 
    future=True,
    poolclass=NullPool,  # Disable SQLAlchemy pooling to avoid conflicts
    connect_args={
        "server_settings": {"jit": "off"},
        "command_timeout": 30,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)
```

### Method 2: Alternative Configuration (if Method 1 fails)
```python
import asyncpg

async def create_connection():
    return await asyncpg.connect(
        DATABASE_URL,
        statement_cache_size=0,
        prepared_statement_cache_size=0
    )

engine = create_async_engine(
    DATABASE_URL,
    creator=create_connection,
    poolclass=NullPool
)
```

## Why This Works

1. **NullPool**: Disables SQLAlchemy's connection pooling, letting PgBouncer handle it
2. **statement_cache_size=0**: Completely disables prepared statement caching
3. **URL Parameters**: Ensures asyncpg gets the configuration directly
4. **Multiple Methods**: Provides redundancy to ensure the fix works

## Testing

After applying the fix, test with multiple database queries to ensure no errors occur.

## Status: ✅ Fixed (Multiple Methods Applied)

This comprehensive fix has been applied to `backend/app/models.py` in the CoachIntel project.
