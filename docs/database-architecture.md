# Database Architecture

This document provides comprehensive documentation on the database architecture of the Simple AI Agent, including PostgreSQL and Redis use cases, schema design, and performance considerations.

## Overview

The Simple AI Agent uses a hybrid database architecture combining:
- **PostgreSQL**: Relational database for persistent storage
- **Redis**: In-memory cache for high-performance session management

This combination provides both data durability and sub-millisecond access times for active conversations.

## PostgreSQL - Relational Data Storage

### Purpose

PostgreSQL serves as the primary persistent storage for all user data, conversations, and messages with ACID transaction guarantees.

### Use Cases

#### 1. User Management
**Purpose**: Store user profiles across multiple channels (Discord, Telegram, Slack)

**Features**:
- Cross-channel user identity management
- User preference storage (preferred AI model)
- User metadata and settings
- Creation and activity timestamps

**Benefits**:
- Single source of truth for user data
- Support for user migration between channels
- Historical user activity tracking

#### 2. Conversation History
**Purpose**: Maintain complete conversation context and history

**Features**:
- Full conversation threading
- Model override per conversation
- Active/inactive conversation state
- Last activity tracking
- Conversation metadata (JSONB for flexibility)

**Benefits**:
- Resume conversations across sessions
- Context-aware AI responses
- Conversation analytics and reporting

#### 3. Message Persistence
**Purpose**: Store all messages for history, context, and analytics

**Features**:
- Message content with role (user/assistant/system)
- Token usage tracking
- Timestamp-based ordering
- Model used for each response
- Metadata storage (JSONB)

**Benefits**:
- Complete audit trail
- Cost analysis via token tracking
- Training data collection
- Compliance and data retention

#### 4. Channel Configuration
**Purpose**: Per-channel settings and defaults

**Features**:
- Default AI model per channel
- Channel-specific settings (JSONB)
- Integration credentials
- Rate limiting configuration

**Benefits**:
- Flexible channel management
- Easy configuration updates
- Multi-tenant support

#### 5. Analytics & Reporting
**Purpose**: Business intelligence and usage analysis

**Features**:
- User engagement metrics
- Model usage statistics
- Conversation patterns
- Performance tracking

**Benefits**:
- Data-driven decisions
- Usage optimization
- Cost tracking and forecasting

### Schema Design

```sql
-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_type VARCHAR(50) NOT NULL,
    channel_user_id VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    preferred_model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    
    UNIQUE (channel_type, channel_user_id),
    INDEX idx_users_channel (channel_type, channel_user_id)
);

-- Conversations Table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL,
    model_override VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    
    INDEX idx_conversations_user (user_id),
    INDEX idx_conversations_activity (last_activity DESC),
    INDEX idx_conversations_active (is_active, user_id)
);

-- Messages Table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    model_used VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    
    INDEX idx_messages_conversation (conversation_id, timestamp DESC),
    INDEX idx_messages_timestamp (timestamp DESC)
);

-- Channel Configs Table
CREATE TABLE channel_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_type VARCHAR(50) NOT NULL UNIQUE,
    default_model VARCHAR(100) NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Performance Optimizations

#### Indexes
- **User Lookup**: `(channel_type, channel_user_id)` composite index for O(1) user lookup
- **Conversation Access**: `user_id` index for fast user conversation retrieval
- **Message History**: `(conversation_id, timestamp)` composite index for efficient pagination
- **Active Conversations**: `(is_active, user_id)` for quick active conversation filtering

#### Connection Pooling
```python
# Async SQLAlchemy with connection pooling
engine = create_async_engine(
    database_url,
    pool_size=20,           # Base connection pool size
    max_overflow=10,        # Additional connections under load
    pool_pre_ping=True,     # Verify connection health
    pool_recycle=3600,      # Recycle connections every hour
    echo=False              # Disable SQL logging in production
)
```

#### Query Optimization
- Use `LIMIT` and `OFFSET` for pagination
- Eager loading with `JOINEDLOAD` to avoid N+1 queries
- Selective column fetching to reduce data transfer
- Prepared statements via SQLAlchemy ORM

#### Future Enhancements
- **Table Partitioning**: Partition `messages` table by month for improved query performance
- **Read Replicas**: Separate read-only replicas for analytics queries
- **Materialized Views**: Pre-computed statistics for dashboards
- **Full-Text Search**: PostgreSQL `tsvector` for message search

## Redis - In-Memory Caching

### Purpose

Redis provides high-speed session caching and real-time data access with sub-millisecond latency.

### Use Cases

#### 1. Session Caching
**Purpose**: Cache active user sessions to avoid database queries

**Data Structure**:
```redis
# Session hash storing all session data
HSET session:discord:user123 user_id "abc-def-123"
HSET session:discord:user123 conversation_id "xyz-789"
HSET session:discord:user123 model "gpt-4"
HSET session:discord:user123 last_activity "2024-01-15T10:30:00Z"

# Auto-expire after 1 hour of inactivity
EXPIRE session:discord:user123 3600
```

**Benefits**:
- ⚡ Sub-millisecond session retrieval
- 🔄 Automatic cleanup via TTL
- 📉 80%+ reduction in database queries
- 💾 Temporary state storage

#### 2. Rate Limiting
**Purpose**: Track and enforce rate limits per user/IP

**Data Structure**:
```redis
# Per-user rate limiting (60 requests/minute)
INCR rate:user:123:minute
EXPIRE rate:user:123:minute 60

# Per-IP rate limiting for webhooks
INCR rate:ip:192.168.1.1:minute
EXPIRE rate:ip:192.168.1.1:minute 60
```

**Benefits**:
- 🛡️ DoS protection
- ⚡ Fast rate check (no database hit)
- 🎯 Granular control (per-user, per-IP, per-endpoint)

#### 3. Active User Tracking
**Purpose**: Track which users are currently active

**Data Structure**:
```redis
# Active users set per channel
SADD active:discord "user123" "user456" "user789"
EXPIRE active:discord 300

# Get active user count
SCARD active:discord

# Check if user is active
SISMEMBER active:discord "user123"
```

**Benefits**:
- 📊 Real-time metrics
- 🎯 Targeted notifications
- 🔄 User presence tracking

#### 4. Conversation Context Cache
**Purpose**: Cache recent conversation context for faster AI responses

**Data Structure**:
```redis
# Store last N messages for quick context building
LPUSH context:conv:xyz messages:json
LTRIM context:conv:xyz 0 19  # Keep last 20 messages
EXPIRE context:conv:xyz 7200 # 2 hour TTL
```

**Benefits**:
- ⚡ Instant context retrieval
- 🧠 Faster AI response times
- 📉 Reduced database load

#### 5. Feature Flags
**Purpose**: Dynamic feature toggles without code deployment

**Data Structure**:
```redis
# Feature flags
HSET features:global enable_mcp_security true
HSET features:global max_conversation_length 100
HSET features:channel:discord enable_slash_commands true

# A/B testing
HSET ab_test:model_selection group:user123 "variant_a"
```

**Benefits**:
- 🚀 Instant feature rollout
- 🎯 A/B testing support
- 🔄 No code deployment needed

### Configuration

#### Redis Settings
```redis
# Persistence (AOF for durability)
appendonly yes
appendfsync everysec

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Save to disk periodically
save 900 1        # After 900 sec if at least 1 key changed
save 300 10       # After 300 sec if at least 10 keys changed
save 60 10000     # After 60 sec if at least 10000 keys changed

# Performance tuning
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

#### Python Client Configuration
```python
# Redis connection with connection pooling
redis_client = redis.from_url(
    redis_url,
    encoding="utf-8",
    decode_responses=True,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True
)
```

### Performance Characteristics

#### Throughput
- **Read Operations**: 100,000+ ops/sec
- **Write Operations**: 80,000+ ops/sec
- **Average Latency**: < 1ms

#### Memory Usage
- **Session Data**: ~1KB per active session
- **Rate Limiting**: ~100B per user/minute
- **Cache Entries**: Varies by data structure

#### Persistence
- **AOF (Append-Only File)**: Durability with minimal performance impact
- **Snapshot (RDB)**: Periodic full backups
- **Replication**: Master-slave setup for high availability

## Hybrid Architecture Benefits

### Performance
- ⚡ **Fast Reads**: 99% of requests served from Redis cache
- 💾 **Reliable Writes**: All data persisted to PostgreSQL
- 🚀 **Low Latency**: Sub-millisecond session access
- 📈 **High Throughput**: Handle thousands of concurrent users

### Scalability
- 📊 **Horizontal Scaling**: Add more Redis nodes for caching
- 🔄 **Read Replicas**: Scale PostgreSQL reads separately
- ⚙️ **Stateless Application**: Multiple app instances share cache and database
- 🌐 **Load Distribution**: Balance between cache and database

### Reliability
- 💪 **Data Durability**: PostgreSQL as source of truth
- 🔄 **Cache Regeneration**: Auto-rebuild cache from database
- 🛡️ **Fault Tolerance**: Continue with degraded performance if Redis fails
- 📦 **Backup & Recovery**: PostgreSQL backups for disaster recovery

### Cost Efficiency
- 💰 **Reduced Database Load**: Lower PostgreSQL instance requirements
- ⚡ **Faster Response Times**: Better user experience
- 📉 **Lower Costs**: Efficient resource utilization

## Monitoring & Maintenance

### PostgreSQL Monitoring
```sql
-- Connection statistics
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Table sizes
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(table_name::regclass)) as total_size
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

### Redis Monitoring
```bash
# Memory usage
redis-cli INFO memory

# Connection stats
redis-cli INFO clients

# Hit rate (should be > 80%)
redis-cli INFO stats | grep keyspace

# Slow queries
redis-cli SLOWLOG GET 10
```

### Health Checks
```python
# Application health check
async def health_check():
    # Check PostgreSQL
    async with db.session() as session:
        await session.execute("SELECT 1")
    
    # Check Redis
    await redis.ping()
    
    return {"status": "healthy", "database": "up", "cache": "up"}
```

## Best Practices

### Session Management
1. ✅ Always set TTL on session keys
2. ✅ Refresh TTL on user activity
3. ✅ Clean up expired sessions
4. ✅ Implement session versioning for schema changes

### Data Consistency
1. ✅ PostgreSQL is source of truth
2. ✅ Cache is disposable and regenerable
3. ✅ Handle cache misses gracefully
4. ✅ Use transactions for multi-table updates

### Performance
1. ✅ Use connection pooling for both databases
2. ✅ Implement query result caching
3. ✅ Monitor cache hit rates
4. ✅ Optimize slow queries with EXPLAIN

### Security
1. ✅ Use parameterized queries (SQLAlchemy ORM)
2. ✅ Encrypt sensitive data at rest
3. ✅ Use SSL/TLS for database connections
4. ✅ Implement proper access control

## Migration Strategy

### Adding a New Table
```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Review generated SQL
alembic upgrade head --sql

# Apply migration
alembic upgrade head
```

### Schema Changes
```python
# Always use migrations for schema changes
# Never modify database directly in production

# Example: Add column with default value
op.add_column('users', 
    sa.Column('timezone', sa.String(50), nullable=True, server_default='UTC')
)
```

### Data Migration
```python
# For complex data migrations
async def migrate_data():
    async with db.session() as session:
        # Batch process to avoid memory issues
        async for batch in get_users_batch(batch_size=1000):
            # Transform data
            for user in batch:
                user.new_field = transform(user.old_field)
            
            await session.commit()
```

## Troubleshooting

### High Database Load
- Check slow query log
- Review missing indexes
- Analyze query execution plans
- Consider read replicas

### Redis Memory Issues
- Review maxmemory-policy
- Check for expired key accumulation
- Monitor key distribution
- Consider Redis Cluster

### Connection Pool Exhaustion
- Increase pool size
- Check for connection leaks
- Review long-running queries
- Implement connection timeout

## Future Enhancements

### PostgreSQL
- [ ] Table partitioning for messages
- [ ] Read replicas for analytics
- [ ] Full-text search with tsvector
- [ ] Materialized views for reporting

### Redis
- [ ] Redis Cluster for horizontal scaling
- [ ] Redis Sentinel for high availability
- [ ] Pub/Sub for real-time notifications
- [ ] RedisJSON for complex data structures

### Architecture
- [ ] CQRS pattern for read/write separation
- [ ] Event sourcing for audit trail
- [ ] Change data capture (CDC) for analytics
- [ ] Time-series database for metrics
