# Transaction Dispute AI Agent

An AI-powered agent for handling transaction disputes in financial apps. It leverages a dynamic **Graph Coloring Scheduler** to organize agent sub-tasks into conflict-free parallel execution batches.

## Project Structure

```text
app/
├── backend/   # FastAPI endpoints, Pydantic schemas, and Graph Scheduler core
└── frontend/  # Streamlit monitoring dashboard
tests/         # Unit and integration test suite
