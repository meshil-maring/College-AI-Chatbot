# College AI Chatbot — Product Overview

## Purpose
An institution-scoped Retrieval-Augmented Generation (RAG) chatbot for colleges. It answers academic questions strictly from institution-owned documents, ensuring responses are grounded in verified, tenant-specific content rather than general LLM knowledge.

## Value Proposition
- Institutions retain full control over the knowledge base (their own uploaded documents)
- Multi-tenant architecture: each college's data is isolated
- Role-based access ensures students, faculty, staff, admins, and super-admins each see only what they're permitted
- Invitation-only Super Admin registration prevents unauthorized platform access

## Key Features

### AI / RAG
- Document ingestion pipeline: PDF, DOCX, XLSX, images → chunked → embedded → stored in pgvector
- Semantic search over institution documents to ground chat responses
- OpenRouter-backed LLM generation with retrieval qualification (decides whether retrieval is needed)
- Public chat endpoint (unauthenticated) and authenticated chat with conversation history

### Knowledge Management
- Document upload to Cloudflare R2 object storage
- Chunking and embedding pipeline with configurable models
- Per-tenant document scoping

### Authentication & Sessions
- Supabase Auth as credential/session provider; backend verifies JWTs server-side
- Rotating refresh tokens, session renewal ~60 s before expiry
- Logout / logout-all / password change / password reset flows
- Rate-limited auth endpoints (process-local counters; gateway limits required in production)
- Invitation-only Super Admin onboarding with single-use SHA-256-digested tokens

### Academic Management
- Academic structure: programs, courses, semesters
- Student registration and approval workflow
- Faculty and staff management
- Learning resources per course

### Multi-Role Platform
| Role | Scope |
|---|---|
| Super Admin | Platform-wide; manages institutions and super admins |
| Admin | Institution-wide; manages users, documents, academic structure |
| Faculty | Course-level; manages resources, views students |
| Staff | Institution support functions |
| Student | Enrolled courses; chat, learning resources |
| Public | Unauthenticated public chat only |

## Target Users
- **College administrators** configuring the platform and uploading institutional documents
- **Students** asking academic questions via chat
- **Faculty** managing course resources
- **Platform operators** (Super Admins) managing multiple institutions
