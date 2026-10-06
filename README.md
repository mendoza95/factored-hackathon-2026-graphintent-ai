# Graph Intent AI Agent

An ML/AI-powered agent for handling transaction disputes/account inquiries within a financial setting. It leverages a dynamic **Graph Coloring Scheduler** to organize dependent sub-tasks into conflict-free parallel execution batches. An ML model classifies user intent and redirects the execution workflow either to the **graph scheduler** to retrieve information from the database or to the **AI bot** to retrieve more information from the user.

## Project Structure

```text
app/
├── backend/   # FastAPI endpoints, Pydantic schemas, and Graph Scheduler core
└── frontend/  # Streamlit monitoring dashboard
tests/         # Unit and integration test suite
