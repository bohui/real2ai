# Real2.AI Service Architecture

This document contains the comprehensive service architecture diagram for the Real2.AI platform, showing how routers/workers consume services, inter-service communication patterns, and client interactions.

## Architecture Overview

The Real2.AI platform follows a layered microservices-inspired architecture with clear separation of concerns:

- **Client Layer**: Web frontend, mobile clients, and external APIs
- **API Gateway Layer**: FastAPI routers handling HTTP requests
- **Service Layer**: Business logic and orchestration services
- **Worker Layer**: Celery background task processors
- **Workflow Engine Layer**: LangGraph-based contract analysis workflows
- **Client Layer**: External service integrations with factory pattern
- **Infrastructure Layer**: Database, caching, storage, and messaging

## Mermaid Architecture Diagram

```mermaid
graph TB
    subgraph "CLIENT LAYER"
        WF[Web Frontend]
        MC[Mobile Client]
        EA[External APIs]
    end

    subgraph "API GATEWAY LAYER"
        subgraph "FastAPI Router Layer"
            CR[contracts router]
            DR[documents router]
            AR[auth router]
            UR[users router]
            WR[websocket router]
            OR[ocr router]
            PR[property router]
            HR[health router]
        end
    end

    subgraph "SERVICE LAYER"
        DS[Document Service]
        CAS[Contract Analysis Service]
        WS[WebSocket Service]
        OS[OCR Service]
        PPS[Property Profile Service]
        PES[Prompt Engineering Service]
        GOS[Gemini OCR Service]
        OPS[OCR Performance Service]
        RPS[Redis PubSub Service]
    end

    subgraph "WORKER LAYER"
        subgraph "Celery Background Workers"
            DPW[Document Processing Worker]
            CAW[Contract Analysis Worker]
            OPW[OCR Processing Worker]
            RGW[Report Generation Worker]
            BPW[Batch Processing Worker]
        end
    end

    subgraph "WORKFLOW ENGINE LAYER"
        subgraph "LangGraph Workflow System"
            VI[validate_input]
            PD[process_document]
            ET[extract_terms]
            AC[analyze_compliance]
            AR2[assess_risks]
            GR[generate_recommendations]
            CR2[compile_report]
            FS[final_state]
            
            VI --> PD
            PD --> ET
            ET --> AC
            AC --> AR2
            AR2 --> GR
            GR --> CR2
            CR2 --> FS
        end
    end

    subgraph "CLIENT LAYER (External Services)"
        subgraph "External Service Clients"
            SC[Supabase Client]
            GC[Gemini Client]
            OC[OpenAI Client]
            CC[CoreLogic Client]
            DC[Domain Client]
            
            CF[Client Factory<br/>DI Container]
            
            CF --> SC
            CF --> GC
            CF --> OC
            CF --> CC
            CF --> DC
        end
    end

    subgraph "INFRASTRUCTURE LAYER"
        DB[(Database<br/>Supabase)]
        RC[(Redis<br/>Cache + Pub/Sub)]
        FS2[(File Store<br/>Supabase)]
        MQ[(Messaging<br/>Celery)]
    end

    %% Client to API Gateway connections
    WF --> CR
    WF --> DR
    WF --> AR
    WF --> UR
    WF --> WR
    MC --> CR
    MC --> DR
    MC --> AR
    EA --> PR
    EA --> HR

    %% API Gateway to Service Layer connections
    CR --> CAS
    DR --> DS
    AR --> DS
    UR --> DS
    WR --> WS
    OR --> OS
    OR --> GOS
    PR --> PPS

    %% Service Layer internal connections
    CAS <--> DS
    CAS <--> WS
    CAS <--> PES
    DS <--> OS
    DS <--> GOS
    WS <--> RPS
    OS <--> OPS

    %% Service to Worker connections
    DS --> DPW
    CAS --> CAW
    OS --> OPW
    GOS --> OPW
    CAS --> RGW
    DS --> BPW

    %% Worker to Workflow connections
    CAW --> VI
    DPW --> PD
    OPW --> ET

    %% Service to External Client connections
    DS --> SC
    CAS --> GC
    CAS --> OC
    PPS --> DC
    PPS --> CC
    OS --> GC
    GOS --> GC

    %% Infrastructure connections
    SC --> DB
    SC --> FS2
    RPS --> RC
    DPW --> MQ
    CAW --> MQ
    OPW --> MQ
    RGW --> MQ
    BPW --> MQ

    %% WebSocket real-time connections
    WS -.->|Real-time updates| WF
    WS -.->|Real-time updates| MC
    RPS -.->|Event notifications| WS

    %% Styling
    classDef clientLayer fill:#e1f5fe
    classDef gatewayLayer fill:#f3e5f5
    classDef serviceLayer fill:#e8f5e8
    classDef workerLayer fill:#fff3e0
    classDef workflowLayer fill:#fce4ec
    classDef externalLayer fill:#f1f8e9
    classDef infraLayer fill:#eceff1

    class WF,MC,EA clientLayer
    class CR,DR,AR,UR,WR,OR,PR,HR gatewayLayer
    class DS,CAS,WS,OS,PPS,PES,GOS,OPS,RPS serviceLayer
    class DPW,CAW,OPW,RGW,BPW workerLayer
    class VI,PD,ET,AC,AR2,GR,CR2,FS workflowLayer
    class SC,GC,OC,CC,DC,CF externalLayer
    class DB,RC,FS2,MQ infraLayer
```

## Communication Patterns

### Synchronous Communication (HTTP REST API)
- **Client ↔ API Gateway**: Standard HTTP request/response
- **API Gateway ↔ Services**: Direct service method calls
- **Services ↔ External Clients**: HTTP API calls with retry logic

### Asynchronous Communication (Background Tasks)
- **Services → Workers**: Celery task queue for heavy processing
- **Workers → Workflows**: LangGraph state-based execution
- **Workers → Infrastructure**: Database and storage operations

### Real-time Communication (WebSocket)
- **Services ↔ Clients**: Bidirectional real-time updates
- **Services ↔ Redis**: Pub/Sub for event distribution
- **Workers → Clients**: Progress notifications via WebSocket

### Event-driven Communication (Redis Pub/Sub)
- **Services → Services**: Event notifications
- **Workers → Services**: Status updates and results
- **System → Clients**: Real-time notifications

## Key Architectural Patterns

### 1. **Factory Pattern** (Client Layer)
- Centralized client creation and configuration
- Dependency injection for service integration
- Standardized error handling and retry logic

### 2. **Observer Pattern** (WebSocket System)
- Real-time event propagation
- Decoupled notification system
- Multi-client broadcast capabilities

### 3. **Command Pattern** (Background Workers)
- Asynchronous task execution
- Task queuing and scheduling
- Progress tracking and result handling

### 4. **State Pattern** (Workflow Engine)
- LangGraph-based state machine
- Sequential processing with error handling
- Progress tracking and recovery

### 5. **Singleton Pattern** (Service Managers)
- WebSocket connection management
- Database connection pooling
- Service registry and lifecycle

## Quality Attributes

### Scalability
- **Horizontal**: Multiple worker instances
- **Vertical**: Async processing and connection pooling
- **Load Distribution**: Celery task distribution

### Reliability
- **Error Handling**: Comprehensive retry mechanisms
- **Graceful Degradation**: Fallback strategies
- **Health Monitoring**: System health endpoints

### Performance
- **Caching**: Redis for frequent data access
- **Background Processing**: Non-blocking operations
- **Connection Pooling**: Efficient resource utilization

### Maintainability
- **Separation of Concerns**: Clear layer boundaries
- **Standardized Interfaces**: Consistent API patterns
- **Comprehensive Logging**: Full system observability

### Security
- **Authentication**: JWT-based auth system
- **Authorization**: Role-based access control
- **Data Protection**: Encrypted storage and transmission

## Data Flow Examples

### Document Upload and Analysis Flow
```
Client → Document Router → Document Service → Supabase Storage
                                ↓
Background Worker → OCR Service → Gemini Client
                                ↓
Contract Analysis Worker → LangGraph Workflow → AI Analysis
                                ↓
WebSocket Service → Real-time Updates → Client
```

### Property Profile Integration Flow
```
Client → Property Router → Property Profile Service → Domain/CoreLogic Client
                                ↓
External API → Data Processing → Database Storage
                                ↓
WebSocket Service → Results → Client
```

### Real-time Progress Updates Flow
```
Background Worker → Progress Update → Redis Pub/Sub
                                ↓
WebSocket Service → Event Handler → Connected Clients
```

This architecture provides a robust, scalable foundation for the Real2.AI Australian real estate contract analysis platform, with clear service boundaries, comprehensive error handling, and real-time user experience capabilities.