# SQLAlchemy + AsyncPG + PgBouncer/Supabase Connection Pooling Fix

## The Problem

When using SQLAlchemy with asyncpg and connection poolers (like Supabase's PgBouncer), you may encounter:

```
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: 
<class 'asyncpg.exceptions.DuplicatePreparedStatementError'>: 
prepared statement "__asyncpg_stmt_3__" already exists
```

## Root Cause

- **Prepared Statements**: AsyncPG creates prepared statements to optimize repeated queries
- **Connection Pooling**: PgBouncer in "transaction" mode doesn't properly handle prepared statements
- **Conflict**: When connections are reused, prepared statements clash

## The Solution

Disable prepared statements in the SQLAlchemy engine configuration:

```python
engine = create_async_engine(
    DATABASE_URL, 
    echo=True, 
    future=True,
    connect_args={
        "statement_cache_size": 0,  # Disable prepared statements
        "prepared_statement_cache_size": 0  # Additional safety
    }
)
```

## Why This Works

1. **No Performance Loss**: For web apps with varied queries, prepared statements don't provide significant benefits
2. **Connection Pool Compatible**: Works seamlessly with PgBouncer and Supabase pooling
3. **Production Ready**: Many production apps use this configuration

## Alternative Solutions

1. **Use AsyncPG's built-in pooling** (instead of PgBouncer)
2. **Switch PgBouncer to "session" mode** (not recommended for Supabase)
3. **Use synchronous SQLAlchemy** (loses async benefits)

## Status: ✅ Fixed

This fix has been applied to `backend/app/models.py` in the CoachIntel project.
