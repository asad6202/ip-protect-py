# Overview

IP Protect is a comprehensive CCTV product quote generation system that leverages AI to convert natural language requests into structured product quotes. The system consists of a FastAPI backend with PostgreSQL database and a React TypeScript frontend, designed for camera equipment distributors to efficiently generate quotes from customer requirements.

The application combines traditional product catalog management with AI-powered intent extraction to match customer needs with specific camera products, NVRs, switches, and accessories from multiple manufacturers (Axis, Hanwha, I-Pro).

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **FastAPI Framework**: RESTful API with automatic OpenAPI documentation
- **Async Database Layer**: PostgreSQL with asyncpg for connection pooling
- **AI Integration**: OpenAI GPT-4o for natural language processing and intent extraction
- **Vector Search**: Optional pgvector extension for semantic product matching
- **Service Layer**: Modular services for quote generation, product retrieval, and data management

## Database Design
- **Product Management**: Brands, products, uploads, and import batches with normalized attributes
- **Quote System**: Complete quote lifecycle with items, feedback, and audit trails
- **Rule Engine**: Configurable business rules for quote generation and validation
- **Audit System**: Comprehensive tracking of prompt runs and quote generation history

## Frontend Architecture
- **React 18** with TypeScript for type safety
- **Vite** for fast development and optimized builds
- **React Router v6** for client-side routing
- **TanStack Query** for server state management and caching
- **shadcn/ui** component library with Tailwind CSS styling
- **Modular Feature Architecture**: Organized by business domains (quotes, products, brands, etc.)

## AI and Search Strategy
- **OpenAI Agent Workflow**: Multi-agent system for intelligent quote generation with safety guardrails
  - Router Agent: Classifies incoming requests (quote_request, rfp, pricing_update, rule_edit)
  - Quote Builder Agent: Generates structured quote data from natural language
  - Guardrails System: PII detection, content moderation, and jailbreak prevention
  - Uses OPENAI_API_KEY from environment secrets for secure API access
- **Intent Extraction**: GPT-4o-powered parsing of natural language requirements into structured search criteria
- **Hybrid Search**: Deterministic keyword matching with optional vector similarity fallback
- **Product Matching**: Family-aware search (camera/NVR/switch) with feature normalization
- **Fallback Handling**: Placeholder items when products aren't found, maintaining quote structure

## Data Processing Pipeline
- **CSV Import**: Automated product data loading from manufacturer price lists
- **Data Normalization**: Extraction of product attributes (form factor, outdoor rating, PoE, IR range)
- **Embedding Generation**: Batch processing for vector search capabilities
- **Brand Management**: Multi-tenant product organization by manufacturer

# External Dependencies

## Core Services
- **OpenAI API**: GPT-4o for natural language processing and text-embedding-3-small for vector embeddings
- **PostgreSQL**: Primary database with optional pgvector extension for semantic search

## Development Tools
- **Python 3.10+**: Backend runtime with FastAPI, asyncpg, and OpenAI libraries
- **Node.js 18+**: Frontend development environment
- **Docker**: Optional containerization for PostgreSQL with pgvector

## Third-party Libraries
- **Backend**: FastAPI, asyncpg, SQLAlchemy, pandas for data processing
- **Frontend**: React Query for API state management, Axios for HTTP requests, react-hook-form with Zod validation
- **UI Components**: Radix UI primitives with shadcn/ui design system

## Optional Integrations
- **Vector Search**: pgvector PostgreSQL extension (graceful degradation without it)
- **File Storage**: Local filesystem for CSV uploads (configurable for cloud storage)
- **Authentication**: Ready for integration (currently single-user system)