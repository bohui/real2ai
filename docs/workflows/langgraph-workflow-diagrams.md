# LangGraph Workflow Architecture - Real2.ai Contract Analysis

## 1. Complete LangGraph Workflow Overview

```mermaid
graph TD
    START([Start]) --> VI[validate_input]
    
    %% Core Processing Flow
    VI --> PD[process_document]
    PD --> ET[extract_terms]
    ET --> AC[analyze_compliance]
    AC --> AR[assess_risks]
    AR --> GR[generate_recommendations]
    GR --> CR[compile_report]
    CR --> END([End])
    
    %% Error Handling Nodes
    HE[handle_error] --> END
    RP[retry_processing]
    
    %% Conditional Decision Points
    PD --> CPS{check_processing_success}
    CPS -->|success| ET
    CPS -->|retry| RP
    CPS -->|error| HE
    
    ET --> CEQ{check_extraction_quality}
    CEQ -->|high_confidence ≥0.7| AC
    CEQ -->|low_confidence 0.4-0.7| RP
    CEQ -->|error <0.4| HE
    
    RP --> PD
    
    %% State Updates
    VI -.-> S1[Update: input_validated]
    PD -.-> S2[Update: document_processed]
    ET -.-> S3[Update: terms_extracted]
    AC -.-> S4[Update: compliance_analyzed]
    AR -.-> S5[Update: risks_assessed]
    GR -.-> S6[Update: recommendations_generated]
    CR -.-> S7[Update: report_compiled]
    
    %% Styling
    classDef processNode fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef decisionNode fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef errorNode fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef stateNode fill:#f3e5f5,stroke:#4a148c,stroke-width:1px
    
    class VI,PD,ET,AC,AR,GR,CR processNode
    class CPS,CEQ decisionNode
    class HE,RP errorNode
    class S1,S2,S3,S4,S5,S6,S7 stateNode
```

## 2. AI Model Integration Architecture

```mermaid
graph TB
    subgraph "Document Processing Layer"
        DOC[Document Input] --> OCR[OCR/Text Extraction]
        OCR --> QA[Quality Assessment]
    end
    
    subgraph "LangGraph Workflow"
        LGW[LangGraph StateGraph]
        STATE[RealEstateAgentState]
    end
    
    subgraph "AI Model Integration Points"
        GPT4[OpenAI GPT-4]
        TOOLS[Australian Tools]
        CONFIDENCE[Confidence Scoring]
    end
    
    subgraph "Australian Domain Intelligence"
        EXTRACT[extract_australian_contract_terms]
        COOLING[validate_cooling_off_period]
        STAMP[calculate_stamp_duty]
        SPECIAL[analyze_special_conditions]
    end
    
    %% Flow connections
    QA --> LGW
    LGW <--> STATE
    
    %% AI Model Calls
    LGW --> EXTRACT
    LGW --> COOLING
    LGW --> STAMP
    LGW --> SPECIAL
    
    %% GPT-4 Integration Points
    LGW --> GPT4
    GPT4 --> |Risk Assessment| RISKLLM[Risk Analysis LLM Call]
    GPT4 --> |Recommendations| RECLLM[Recommendations LLM Call]
    
    %% Confidence Flow
    EXTRACT --> CONFIDENCE
    COOLING --> CONFIDENCE
    STAMP --> CONFIDENCE
    SPECIAL --> CONFIDENCE
    RISKLLM --> CONFIDENCE
    RECLLM --> CONFIDENCE
    
    CONFIDENCE --> STATE
    
    %% Styling
    classDef aiModel fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    classDef workflow fill:#2196f3,stroke:#0d47a1,stroke-width:2px,color:#fff
    classDef tools fill:#ff9800,stroke:#e65100,stroke-width:2px
    classDef state fill:#9c27b0,stroke:#4a148c,stroke-width:2px,color:#fff
    
    class GPT4,RISKLLM,RECLLM aiModel
    class LGW workflow
    class EXTRACT,COOLING,STAMP,SPECIAL tools
    class STATE,CONFIDENCE state
```

## 3. State Management and Data Flow

```mermaid
sequenceDiagram
    participant User as User
    participant API as FastAPI
    participant WF as LangGraph Workflow
    participant State as RealEstateAgentState
    participant Tools as AU Tools
    participant GPT4 as OpenAI GPT-4
    participant WS as WebSocket
    
    User->>API: Upload Contract PDF
    API->>WF: Start Analysis
    
    rect rgb(240, 248, 255)
        Note over WF,State: Input Validation Phase
        WF->>State: validate_input()
        State-->>WF: input_validated
        WF->>WS: Progress: 10%
    end
    
    rect rgb(245, 255, 245)
        Note over WF,Tools: Document Processing Phase
        WF->>State: process_document()
        State->>Tools: Extract text content
        Tools-->>State: Extracted text + confidence
        State-->>WF: document_processed
        WF->>WS: Progress: 25%
    end
    
    rect rgb(255, 248, 240)
        Note over WF,Tools: Term Extraction Phase
        WF->>Tools: extract_australian_contract_terms()
        Tools->>Tools: Pattern matching + validation
        Tools-->>State: Contract terms + confidence
        State-->>WF: terms_extracted
        WF->>WS: Progress: 45%
    end
    
    rect rgb(248, 240, 255)
        Note over WF,Tools: Compliance Analysis Phase
        WF->>Tools: validate_cooling_off_period()
        WF->>Tools: calculate_stamp_duty()
        WF->>Tools: analyze_special_conditions()
        Tools-->>State: Compliance results
        State-->>WF: compliance_analyzed
        WF->>WS: Progress: 65%
    end
    
    rect rgb(255, 240, 240)
        Note over WF,GPT4: Risk Assessment Phase (AI)
        WF->>GPT4: Risk assessment prompt
        GPT4-->>WF: Risk analysis JSON
        WF->>State: risks_assessed
        WF->>WS: Progress: 80%
    end
    
    rect rgb(240, 255, 240)
        Note over WF,GPT4: Recommendations Phase (AI)
        WF->>GPT4: Recommendations prompt
        GPT4-->>WF: Recommendations JSON
        WF->>State: recommendations_generated
        WF->>WS: Progress: 90%
    end
    
    rect rgb(248, 248, 255)
        Note over WF,State: Report Compilation Phase
        WF->>State: compile_report()
        State->>State: Calculate overall confidence
        State-->>WF: report_compiled
        WF->>WS: Progress: 100% - Complete
    end
    
    WF-->>API: Final analysis results
    API-->>User: Analysis complete
```

## 4. Confidence Scoring System

```mermaid
graph TD
    subgraph "Confidence Input Sources"
        DOC[Document Parsing<br/>Weight: 0.2]
        EXTRACT[Term Extraction<br/>Weight: 0.3]
        RISK[Risk Assessment<br/>Weight: 0.25]
        COMP[Compliance Check<br/>Weight: 0.25]
    end
    
    subgraph "Confidence Calculation Engine"
        CALC[Weighted Average Calculator]
        ALGO["weighted_sum = Σ(score × weight)<br/>confidence = weighted_sum / total_weight"]
    end
    
    subgraph "Quality Gates"
        HIGH[High Confidence ≥ 0.7<br/>✅ Continue Processing]
        MED[Medium Confidence 0.4-0.7<br/>⚠️ Flag for Review]
        LOW[Low Confidence < 0.4<br/>❌ Trigger Retry/Error]
    end
    
    subgraph "Routing Logic"
        CONT[Continue to Next Step]
        RETRY[Retry Current Step]
        ERROR[Handle Error]
    end
    
    DOC --> CALC
    EXTRACT --> CALC
    RISK --> CALC
    COMP --> CALC
    
    CALC --> ALGO
    ALGO --> DECISION{Confidence Score?}
    
    DECISION -->|≥ 0.7| HIGH
    DECISION -->|0.4-0.7| MED
    DECISION -->|< 0.4| LOW
    
    HIGH --> CONT
    MED --> CONT
    LOW --> RETRY
    
    RETRY -->|Max Retries Reached| ERROR
    
    %% Styling
    classDef input fill:#e8f5e8,stroke:#2e7d32
    classDef calc fill:#e3f2fd,stroke:#1565c0
    classDef gate fill:#fff3e0,stroke:#ef6c00
    classDef action fill:#fce4ec,stroke:#c2185b
    
    class DOC,EXTRACT,RISK,COMP input
    class CALC,ALGO calc
    class HIGH,MED,LOW gate
    class CONT,RETRY,ERROR action
```

## 5. Error Handling and Recovery Flow

```mermaid
graph TD
    START[Processing Step] --> EXEC[Execute Node Logic]
    
    EXEC --> CHECK{Error Occurred?}
    CHECK -->|No| SUCCESS[Update State - Success]
    CHECK -->|Yes| ERROR_TYPE{Error Type?}
    
    ERROR_TYPE -->|Processing Error| DOC_ERROR[Document Processing Failed]
    ERROR_TYPE -->|Extraction Error| EXT_ERROR[Term Extraction Failed]
    ERROR_TYPE -->|LLM Error| LLM_ERROR[AI Model Call Failed]
    ERROR_TYPE -->|Workflow Error| WORK_ERROR[Workflow Exception]
    
    DOC_ERROR --> RETRY_CHECK{Retry Count < 2?}
    EXT_ERROR --> RETRY_CHECK
    LLM_ERROR --> FALLBACK[Use Fallback Response]
    WORK_ERROR --> HANDLE_ERROR
    
    RETRY_CHECK -->|Yes| INC_RETRY[Increment Retry Count]
    RETRY_CHECK -->|No| HANDLE_ERROR[Handle Error Node]
    
    INC_RETRY --> RETRY_NODE[retry_processing]
    RETRY_NODE --> EXEC
    
    FALLBACK --> DEGRADED[Degraded Processing]
    DEGRADED --> SUCCESS
    
    HANDLE_ERROR --> LOG[Log Error Details]
    LOG --> ERROR_STATE[Create Error State]
    ERROR_STATE --> TERMINATE[Terminate Workflow]
    
    SUCCESS --> NEXT[Continue to Next Node]
    
    %% Confidence-based routing
    SUCCESS --> CONF_CHECK{Confidence Check}
    CONF_CHECK -->|High| NEXT
    CONF_CHECK -->|Low| RETRY_CHECK
    
    %% Styling
    classDef normal fill:#e1f5fe,stroke:#01579b
    classDef error fill:#ffebee,stroke:#c62828
    classDef retry fill:#fff3e0,stroke:#ef6c00
    classDef success fill:#e8f5e8,stroke:#2e7d32
    
    class START,EXEC,CHECK,SUCCESS,NEXT normal
    class DOC_ERROR,EXT_ERROR,LLM_ERROR,WORK_ERROR,HANDLE_ERROR,ERROR_STATE,TERMINATE error
    class RETRY_CHECK,INC_RETRY,RETRY_NODE,FALLBACK,DEGRADED retry
    class CONF_CHECK success
```

## 6. Australian Tools Integration Details

```mermaid
graph TB
    subgraph "Australian Legal Framework"
        NSW[NSW Rules]
        VIC[VIC Rules]
        QLD[QLD Rules]
        SA[SA Rules]
        WA[WA Rules]
        TAS[TAS Rules]
        NT[NT Rules]
        ACT[ACT Rules]
    end
    
    subgraph "Term Extraction Tool"
        PATTERNS[Regex Patterns<br/>• Purchase Price<br/>• Deposit Amount<br/>• Settlement Date<br/>• Cooling Off Period<br/>• Property Address]
        
        VALIDATION[State Validation<br/>• Legal Requirements<br/>• Format Checking<br/>• Confidence Scoring]
    end
    
    subgraph "Compliance Tools"
        COOLING_TOOL[Cooling Off Validation<br/>• 2-5 days by state<br/>• Business vs clear days<br/>• Waiver rules<br/>• Legal references]
        
        STAMP_TOOL[Stamp Duty Calculator<br/>• Progressive rates<br/>• First home exemptions<br/>• Foreign buyer surcharge<br/>• Investment property tax]
        
        SPECIAL_TOOL[Special Conditions Analyzer<br/>• Finance clauses<br/>• Building/pest inspection<br/>• Strata searches<br/>• Council certificates]
    end
    
    subgraph "Integration Flow"
        INPUT[Contract Text + State] --> PATTERNS
        PATTERNS --> EXTRACTION[Extracted Terms]
        EXTRACTION --> COOLING_TOOL
        EXTRACTION --> STAMP_TOOL
        EXTRACTION --> SPECIAL_TOOL
        
        COOLING_TOOL --> COMPLIANCE[Compliance Report]
        STAMP_TOOL --> FINANCIAL[Financial Analysis]
        SPECIAL_TOOL --> RISKS[Risk Factors]
    end
    
    %% State-specific connections
    NSW -.-> COOLING_TOOL
    VIC -.-> COOLING_TOOL
    QLD -.-> COOLING_TOOL
    SA -.-> COOLING_TOOL
    WA -.-> COOLING_TOOL
    TAS -.-> COOLING_TOOL
    NT -.-> COOLING_TOOL
    ACT -.-> COOLING_TOOL
    
    NSW -.-> STAMP_TOOL
    VIC -.-> STAMP_TOOL
    QLD -.-> STAMP_TOOL
    SA -.-> STAMP_TOOL
    WA -.-> STAMP_TOOL
    
    %% Output integration
    COMPLIANCE --> OUTPUT[Analysis Results]
    FINANCIAL --> OUTPUT
    RISKS --> OUTPUT
    
    %% Styling
    classDef state fill:#e8eaf6,stroke:#3f51b5
    classDef tool fill:#e0f2f1,stroke:#00695c
    classDef flow fill:#fff3e0,stroke:#ef6c00
    classDef output fill:#fce4ec,stroke:#c2185b
    
    class NSW,VIC,QLD,SA,WA,TAS,NT,ACT state
    class PATTERNS,VALIDATION,COOLING_TOOL,STAMP_TOOL,SPECIAL_TOOL tool
    class INPUT,EXTRACTION,COMPLIANCE,FINANCIAL,RISKS flow
    class OUTPUT output
```

## 7. Performance Optimization Opportunities

```mermaid
graph TD
    subgraph "Current Bottlenecks"
        SEQ[Sequential LLM Calls<br/>Risk + Recommendations<br/>3-5 seconds each]
        
        DOC_PROC[Document Processing<br/>OCR dependency<br/>2-5 seconds]
        
        STATE_SIZE[Large State Objects<br/>Full document content<br/>Memory overhead]
        
        NO_CACHE[No Result Caching<br/>Repeated processing<br/>Same documents]
    end
    
    subgraph "Optimization Strategies"
        PARALLEL[Parallel Processing<br/>• Concurrent LLM calls<br/>• Independent analysis branches<br/>• Async tool execution]
        
        STREAM[Streaming Results<br/>• Progressive updates<br/>• Partial result delivery<br/>• Real-time feedback]
        
        CACHE[Intelligent Caching<br/>• Document hash caching<br/>• Tool result caching<br/>• State compression]
        
        PREPROC[Document Preprocessing<br/>• Image enhancement<br/>• Format optimization<br/>• Quality assessment]
    end
    
    subgraph "Implementation Plan"
        PHASE1[Phase 1: Parallel Tools<br/>• Concurrent AU tools<br/>• Async state updates<br/>• 30% time reduction]
        
        PHASE2[Phase 2: LLM Optimization<br/>• Parallel risk/recommendations<br/>• Streaming responses<br/>• 40% time reduction]
        
        PHASE3[Phase 3: Caching Layer<br/>• Result caching<br/>• State optimization<br/>• 60% reduction repeated docs]
    end
    
    %% Current bottleneck flows
    SEQ --> IMPACT1[7-15 seconds total processing]
    DOC_PROC --> IMPACT1
    STATE_SIZE --> IMPACT2[High memory usage]
    NO_CACHE --> IMPACT3[Redundant processing]
    
    %% Optimization flows
    PARALLEL --> BENEFIT1[3-8 seconds processing]
    STREAM --> BENEFIT2[Better UX]
    CACHE --> BENEFIT3[Instant repeated results]
    PREPROC --> BENEFIT4[Higher OCR accuracy]
    
    %% Implementation progression
    PHASE1 --> PHASE2
    PHASE2 --> PHASE3
    
    %% Styling
    classDef bottleneck fill:#ffebee,stroke:#c62828
    classDef optimization fill:#e8f5e8,stroke:#2e7d32
    classDef implementation fill:#e3f2fd,stroke:#1565c0
    classDef impact fill:#fff3e0,stroke:#ef6c00
    
    class SEQ,DOC_PROC,STATE_SIZE,NO_CACHE bottleneck
    class PARALLEL,STREAM,CACHE,PREPROC optimization
    class PHASE1,PHASE2,PHASE3 implementation
    class IMPACT1,IMPACT2,IMPACT3,BENEFIT1,BENEFIT2,BENEFIT3,BENEFIT4 impact
```

## Key Architecture Insights

### **Strengths of Current Design**
- **Robust Error Handling**: Multi-level error recovery with graceful degradation
- **Domain Expertise**: Deep Australian property law integration
- **Quality Gates**: Confidence-based routing ensures reliability
- **Real-time Updates**: WebSocket integration for user experience

### **Optimization Opportunities**
- **Parallel Processing**: Independent analysis branches can run concurrently
- **Caching Strategy**: Document and tool result caching for performance
- **State Optimization**: Lightweight state management with references
- **Streaming Results**: Progressive result delivery for better UX

### **Scalability Considerations**
- **Workflow Orchestration**: LangGraph provides excellent scalability foundation
- **Resource Management**: Need connection pooling and rate limiting
- **Cost Optimization**: Intelligent LLM usage based on confidence scores
- **Monitoring**: Comprehensive logging and metrics for production operations

This architecture demonstrates sophisticated AI workflow orchestration with strong domain expertise and clear paths for optimization and scaling.