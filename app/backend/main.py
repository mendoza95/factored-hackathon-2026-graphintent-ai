from fastapi import FastAPI

app = FastAPI(
    title="Transaction Dispute AI Agent API",
    version="0.1.0",
    description="API for transaction dispute agent powered by dynamic Graph Coloring",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
