# Overview

The IP Protect application is a comprehensive quote generation system for CCTV surveillance products. It features an AI-powered natural language interface that allows users to request security equipment quotes using plain English descriptions. The system extracts product requirements, searches a catalog of over 3,500 products from brands like Axis, Hanwha, and I-Pro, and generates structured quotes with pricing and technical specifications.

The application combines natural language processing with deterministic product matching to provide accurate quotes for cameras, NVRs, switches, and accessories. It includes both a FastAPI backend with PostgreSQL database and a modern React frontend for complete quote management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture

**Framework**: FastAPI with Python 3.10+, providing async REST API endpoints with automatic OpenAPI documentation.

**Database**: PostgreSQL with optional pgvector extension for semantic search capabilities. The schema includes tables for brands, products, quotes, quote items, feedback, rules, and audit trails.

**AI Integration**: OpenAI GPT-4o-mini for intent extraction from natural language prompts, plus text-embedding-3-small for vector embeddings when pgvector is available.

**Search Strategy**: Hybrid approach combining deterministic SQL-based product matching with optional vector similarity search fallback. Includes family-aware filtering, brand preferences, budget constraints, and feature matching.

**Data Loading**: CSV import system supporting bulk product uploads with automatic brand extraction and feature normalization.

## Frontend Architecture

**Framework**: React 18 with TypeScript, using Vite for build tooling and development server.

**Routing**: React Router v6 for client-side navigation with nested route structure.

**State Management**: TanStack React Query for server state management, caching, and data synchronization.

**UI Components**: shadcn/ui component library built on Radix UI primitives with Tailwind CSS for styling.

**Forms**: react-hook-form with Zod validation for type-safe form handling.

## Core Services

**Quote Service**: Handles quote creation, management, and persistence with support for draft/finalized states and item-level tracking.

**Retrieval Service**: Implements the product search logic with scoring algorithms, family mapping, and feature extraction.

**Intent Extractor**: Parses natural language requests into structured JSON with normalized technical specifications and quantities.

## Database Design

**Single-User Schema**: Optimized for quote generation workflows without complex user management or multi-tenancy.

**Product Catalog**: Normalized product data with brand relationships, technical attributes, and optional vector embeddings.

**Quote Management**: Hierarchical structure with quotes containing multiple items, supporting metadata, feedback, and status tracking.

**Rule Engine**: Configurable business rules for quote customization and automated recommendations.

# External Dependencies

**OpenAI API**: Required for natural language processing and intent extraction. Uses GPT-4o-mini for structured JSON extraction and text-embedding-3-small for vector embeddings.

**PostgreSQL Database**: Primary data store with required extensions including pgcrypto, pg_trgm, and unaccent. Optional pgvector extension enhances search capabilities with semantic similarity.

**Node.js Runtime**: Frontend requires Node.js 18+ for development and build processes.

**CSV Data Sources**: Product catalog populated from manufacturer price lists in CSV format, supporting Axis, Hanwha, and I-Pro product lines.

The system is designed to work with or without the pgvector extension, gracefully falling back to deterministic search when vector capabilities are unavailable.