Think deeply before implementing. Spend significant effort on software architecture and planning before writing code. When making technical decisions, prefer long-term maintainability, security, and production readiness over the quickest implementation. Challenge assumptions, justify architectural choices, and continuously critique and improve your own design throughout the project.

---

# Parking Space Reservation Chatbot – Technical Specification & Implementation Instructions

## Your Role

You are acting as a **Senior AI Architect, Senior Python Engineer, and Technical Lead** responsible for designing and implementing a production-quality AI system.

Your goal is **not only to implement the requested functionality**, but also to produce a maintainable, extensible, secure, well-tested, and production-ready solution.

Whenever requirements are ambiguous:

* Analyze the ambiguity.
* Explain the available options.
* Recommend the best approach based on industry best practices.
* Ask for clarification only if the ambiguity blocks implementation.
* Otherwise, make a reasonable engineering decision and document it.

Do **not** blindly implement poor architectural decisions. If you identify a better approach, explain it before implementation.

---

# Development Workflow

Follow this workflow throughout the project.

## Phase 1 — Requirements Analysis

Before writing any code:

1. Analyze the complete specification.
2. Identify ambiguities or missing requirements.
3. Identify possible architectural improvements.
4. Propose the overall architecture.
5. Explain all major design decisions.
6. Wait for my approval before implementation.

---

## Phase 2 — Incremental Development

Implement **one stage at a time**.

After completing each stage:

* Explain the implementation.
* Explain architectural decisions.
* Explain tradeoffs.
* Provide updated documentation.
* Provide tests.
* Suggest improvements for future stages.
* Wait for approval before moving to the next stage.

Do **not** implement future stages early.

---

# General Technical Requirements

Programming Language:

* Python 3.12+

Frameworks:

* LangChain
* LangGraph

Architecture:

* Retrieval-Augmented Generation (RAG)

Vector Database (choose the best option and justify your decision):

* Milvus
* Pinecone
* Weaviate

Backend API:

* Prefer FastAPI unless another solution is significantly better.

SQL Database:

Choose an appropriate SQL database (SQLite for local development is acceptable; PostgreSQL is preferred if justified).

---

# Engineering Standards

Treat this project as if it will later be deployed into production.

The implementation should follow:

* Clean Architecture
* SOLID principles
* Separation of concerns
* Modular design
* Dependency Injection where appropriate
* Type hints everywhere
* Pydantic models
* Small, testable functions
* Proper exception handling
* Logging
* Configuration through environment variables
* No hardcoded secrets
* Consistent naming conventions
* Comprehensive documentation

Avoid:

* Tutorial-style code
* Placeholder implementations
* Hardcoded values
* Global mutable state
* Unnecessary complexity

---

# General Features

The chatbot should provide:

* General parking information
* Working hours
* Prices
* Parking availability
* Parking location

The chatbot must support reservation creation by interactively collecting:

* Name
* Surname
* Car number
* Reservation period

The chatbot should naturally guide the user through missing information.

---

# Data Architecture

The solution may be improved by separating data into two categories.

## Static Data

Examples:

* General information
* Parking details
* Parking location
* Reservation process

Store static data inside the vector database.

---

## Dynamic Data

Examples:

* Space availability
* Working hours
* Prices

Store dynamic data inside an SQL database.

If another architecture is significantly better, explain why before implementing.

---

# Security Requirements

Implement guardrails to prevent:

* Prompt injection
* Jailbreak attempts
* Exposure of sensitive information
* Retrieval of private/internal documents
* Leakage of vector database contents
* Invalid user input
* Unauthorized access

Use appropriate filtering and validation mechanisms.

If using existing libraries or pretrained NLP models improves security, explain and implement them.

---

# RAG Requirements

Implement a complete RAG pipeline including:

* Document loading
* Document chunking strategy
* Embedding generation
* Vector indexing
* Retrieval
* Metadata filtering
* Prompt templates
* Source attribution where appropriate
* Configurable Top-K retrieval

Clearly explain design decisions.

---

# Evaluation Requirements

Evaluate the RAG system.

Include:

Performance:

* Response latency
* Throughput

Retrieval Quality:

* Recall@K
* Precision@K

If appropriate, recommend or implement additional metrics such as:

* MRR
* Faithfulness
* Context Precision
* Context Recall
* Hallucination detection
* RAGAS evaluation

---

# Testing Requirements

Each module must include at least **2 automated tests**.

Testing should include:

* Unit tests
* Integration tests where appropriate

Use:

* pytest (preferred)

or

* unittest

Where appropriate, mock:

* LLM calls
* Vector database
* External APIs

---

# Documentation Requirements

Every stage must include:

* README
* Setup instructions
* Usage guide
* Project structure
* Configuration guide
* Environment variables
* Architecture explanation
* Design decisions

Whenever possible include diagrams (Mermaid is acceptable):

* Architecture diagram
* Sequence diagram
* LangGraph workflow

---

# CI/CD Requirements

Evaluate whether Infrastructure as Code (Terraform) is justified.

If Terraform is unnecessary, explain why.

Recommend the best CI/CD solution.

Prefer GitHub Actions.

Pipeline should include:

* Formatting
* Linting
* Type checking
* Unit tests
* Integration tests
* Coverage report
* Docker build
* Security scanning

---

# Docker

The project should be easy to run locally.

Prefer Docker Compose.

Containerize components where appropriate.

---

# Stage 1 — RAG Chatbot

## Tasks

Implement the basic chatbot architecture using Retrieval-Augmented Generation.

Integrate a vector database.

Store:

Static information inside the vector database.

Dynamic information inside the SQL database.

Implement interactive chatbot functionality:

* Provide parking information.
* Collect reservation details.

Implement guardrails to prevent sensitive information leakage.

Evaluate:

* Performance
* Retrieval quality

---

## Outcome

A working chatbot capable of:

* Providing information
* Collecting reservation requests
* Protecting sensitive information

Provide:

* README
* Tests
* Evaluation report
* CI/CD recommendation
* Infrastructure recommendation

---

# Stage 2 — Human-in-the-Loop Agent

## Tasks

Create a second LangChain agent responsible for administrator interaction.

After collecting reservation details:

The chatbot should send a reservation request to the administrator.

Possible communication channels:

* Email
* Messenger
* REST API

The administrator should:

* Approve
* Reject

The first agent should receive the administrator decision.

Maintain communication between both agents.

---

## Suggested Reservation Lifecycle

Reservation Created

↓

Pending Approval

↓

Administrator Review

↓

Approved / Rejected

↓

Notify User

↓

Continue Workflow

---

## Outcome

Automated reservation approval system.

Provide:

* README
* Tests
* CI/CD recommendation
* Infrastructure recommendation

---

# Stage 3 — MCP Server

## Tasks

Use an open-source MCP server capable of writing files.

If none is suitable:

Develop a simple MCP server using:

* Python
* FastAPI

If MCP implementation is not feasible, use tool/function calling for writing to file.

After administrator approval:

Write reservation information into a text file.

Format:

Name | Car Number | Reservation Period | Approval Time

The server should be:

* Secure
* Reliable
* Resistant to unauthorized access

If appropriate, expose tools such as:

* save_reservation
* list_reservations
* find_reservation
* health_check

---

## Outcome

Working MCP server integrated with previous stages.

Provide:

* README
* Tests
* CI/CD recommendation
* Infrastructure recommendation

---

# Stage 4 — LangGraph Orchestration

## Tasks

Implement orchestration using LangGraph.

The workflow should integrate:

* User interaction
* RAG retrieval
* Reservation state
* Administrator approval
* MCP communication
* Data persistence

Suggested graph nodes:

* User Input
* Retrieval
* Context Validation
* Response Generation
* Reservation State
* Human Approval
* Approval Result
* MCP Communication
* Persistence
* Error Handling

Maintain graph state using typed state objects.

Test the entire workflow.

---

## Outcome

A unified system where all components work together seamlessly.

Provide:

* README
* Tests
* Documentation
* CI/CD recommendation
* Infrastructure recommendation

---

# System Testing

Conduct:

Load testing for:

* Chatbot
* Administrator workflow
* MCP server

Integration testing across the entire orchestration pipeline.

Measure:

* Latency
* Reliability
* Retrieval quality

Document findings.

---

# Final Deliverables

The completed project should include:

* Production-quality Python code
* Clean Architecture
* LangChain
* LangGraph
* RAG implementation
* Vector database
* SQL database
* Human-in-the-loop agent
* MCP server
* LangGraph orchestration
* Docker support
* Comprehensive README
* Architecture documentation
* Automated tests
* CI/CD pipeline
* Security mechanisms
* Performance evaluation
* Retrieval evaluation
* Well-documented code

---

# Quality Expectations

The implementation will be evaluated not only on correctness but also on software engineering quality.

Avoid simplistic or tutorial-style implementations.

Prioritize:

* Maintainability
* Extensibility
* Security
* Scalability
* Testability
* Readability
* Production readiness

If the code is poor quality, overly simplistic, impractical, or contains significant architectural or implementation flaws, the project grade may be reduced. Therefore, continuously review your own work, identify weaknesses, and refactor where appropriate before presenting the solution.

