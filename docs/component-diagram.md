# Component Diagram

This diagram shows the high-level components of the Clawbot AI Agent system and their interactions.

## System Components

```mermaid
flowchart TB
    subgraph External["External Services"]
        Discord["Discord Platform"]
        Telegram["Telegram Platform"]
        GitHub["GitHub Models API"]
    end

    subgraph Presentation["Presentation Layer"]
        DA["Discord Adapter"]
        TA["Telegram Adapter"]
        Router["Message Router"]
    end

    subgraph Application["Application Layer"]
        MH["Message Handler"]
        SM["Session Manager"]
    end

    subgraph Domain["Domain Layer"]
        GHClient["GitHub Models Client"]
        MS["Model Selector"]
        CB["Context Builder"]
        PM["Prompt Manager"]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        subgraph Database["Database"]
            PG[("PostgreSQL<br/>Users, Conversations,<br/>Messages")]
        end
        subgraph Cache["Cache"]
            Redis[("Redis<br/>Session Cache")]
        end
        subgraph Repos["Repositories"]
            UR["User Repository"]
            CR["Conversation Repository"]
            MR["Message Repository"]
            CCR["Channel Config Repository"]
        end
    end

    subgraph API["API Layer"]
        FastAPI["FastAPI Server"]
        Health["Health Endpoints"]
        Webhooks["Webhook Endpoints"]
    end

    %% External to Presentation
    Discord -->|Messages| DA
    Telegram -->|Updates| TA
    GitHub -->|AI Responses| GHClient

    %% Presentation Layer
    DA -->|ChannelMessage| Router
    TA -->|ChannelMessage| Router
    Router -->|Route| MH

    %% Application Layer
    MH -->|Get/Create Session| SM
    MH -->|Process Commands| MH
    MH -->|Build Context| CB
    MH -->|Select Model| MS
    MH -->|Generate Response| GHClient

    %% Domain Layer
    MS -->|Query Preferences| UR
    MS -->|Query Preferences| CR
    MS -->|Query Preferences| CCR
    CB -->|Load Messages| MR
    CB -->|Save Messages| MR
    GHClient -->|API Calls| GitHub

    %% Session Management
    SM -->|Cache Lookup| Redis
    SM -->|DB Queries| UR
    SM -->|DB Queries| CR

    %% Repository Layer
    UR -->|CRUD| PG
    CR -->|CRUD| PG
    MR -->|CRUD| PG
    CCR -->|CRUD| PG

    %% API Layer
    Webhooks -->|Telegram Updates| TA
    Health -->|Check| PG
    Health -->|Check| Redis
    FastAPI -->|Serve| Health
    FastAPI -->|Serve| Webhooks

    %% Response Flow
    Router -->|Send Response| DA
    Router -->|Send Response| TA
    DA -->|Reply| Discord
    TA -->|Reply| Telegram

    %% Styling
    classDef external fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef presentation fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef application fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef domain fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef infrastructure fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef api fill:#fff9c4,stroke:#f57f17,stroke-width:2px

    class Discord,Telegram,GitHub external
    class DA,TA,Router presentation
    class MH,SM application
    class GHClient,MS,CB,PM domain
    class PG,Redis,UR,CR,MR,CCR infrastructure
    class FastAPI,Health,Webhooks api
```

## Component Descriptions

### External Services

- **Discord Platform**: Discord messaging service
- **Telegram Platform**: Telegram messaging service
- **GitHub Models API**: AI model inference API (GPT-4, Claude, Llama)

### Presentation Layer

- **Discord Adapter**: Handles Discord bot protocol and message conversion
- **Telegram Adapter**: Handles Telegram bot protocol and message conversion
- **Message Router**: Routes messages between channels and message handler

### Application Layer

- **Message Handler**: Orchestrates message processing workflow
- **Session Manager**: Manages user session lifecycle and caching

### Domain Layer

- **GitHub Models Client**: Communicates with GitHub Models API
- **Model Selector**: Determines which AI model to use
- **Context Builder**: Constructs conversation context from history
- **Prompt Manager**: Manages system prompts and templates

### Infrastructure Layer

- **PostgreSQL**: Persistent storage for users, conversations, and messages
- **Redis**: In-memory cache for active sessions
- **User Repository**: Data access for users
- **Conversation Repository**: Data access for conversations
- **Message Repository**: Data access for messages
- **Channel Config Repository**: Data access for channel configurations

### API Layer

- **FastAPI Server**: HTTP server for webhooks and health checks
- **Health Endpoints**: `/health` and `/ready` endpoints
- **Webhook Endpoints**: Receives webhook callbacks from channels

## Data Flow Patterns

### 1. Message Ingestion (Push)
```
Discord/Telegram → Adapter → Router → Message Handler
```

### 2. Message Processing
```
Message Handler → Session Manager → Repositories → Database
Message Handler → Context Builder → Message Repository
Message Handler → Model Selector → Channel Config Repository
Message Handler → GitHub Client → External API
```

### 3. Response Delivery
```
Message Handler → Router → Adapter → Discord/Telegram
```

### 4. Session Caching
```
Session Manager → Redis (fast path)
Session Manager → Repositories → PostgreSQL (slow path)
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Channels | discord.py, python-telegram-bot |
| Application | Python 3.12 (asyncio) |
| AI Integration | OpenAI SDK (GitHub Models) |
| Web Framework | FastAPI, Uvicorn |
| Database | PostgreSQL 16, SQLAlchemy (async) |
| Cache | Redis 7, redis-py (async) |
| Container | Docker, Docker Compose |
| Validation | Pydantic v2 |
| Logging | structlog |

## Deployment View

```mermaid
flowchart TB
    subgraph Docker["Docker Compose"]
        subgraph AppContainer["App Container"]
            App["Clawbot Application<br/>(Python 3.12)"]
        end
        subgraph DBContainer["PostgreSQL Container"]
            DB[("PostgreSQL 16")]
        end
        subgraph CacheContainer["Redis Container"]
            Cache[("Redis 7")]
        end
    end

    Internet["Internet"]
    
    Internet -->|Port 8000| App
    App -->|Port 5432| DB
    App -->|Port 6379| Cache
    
    classDef container fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    class AppContainer,DBContainer,CacheContainer container
```

## Security Boundaries

```mermaid
flowchart LR
    subgraph Untrusted["Untrusted Zone"]
        Users["Discord/Telegram Users"]
    end
    
    subgraph DMZ["DMZ"]
        Adapters["Channel Adapters<br/>(Input Validation)"]
        API["FastAPI<br/>(Rate Limiting)"]
    end
    
    subgraph Trusted["Trusted Zone"]
        App["Application Logic"]
        DB[("Database")]
        Cache[("Cache")]
    end
    
    subgraph External["External (TLS)"]
        GH["GitHub Models API"]
    end
    
    Users -->|Messages| Adapters
    Adapters -->|Validated| App
    API -->|Validated| App
    App -->|Queries| DB
    App -->|Queries| Cache
    App -->|HTTPS| GH
    
    classDef untrusted fill:#ffebee,stroke:#c62828
    classDef dmz fill:#fff3e0,stroke:#ef6c00
    classDef trusted fill:#e8f5e9,stroke:#2e7d32
    classDef external fill:#e1f5fe,stroke:#0277bd
    
    class Users untrusted
    class Adapters,API dmz
    class App,DB,Cache trusted
    class GH external
```
