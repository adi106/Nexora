from fastapi import FastAPI

app = FastAPI(
    title="NEXORA API",
    description="AI-powered e-commerce platform",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "NEXORA API",
    }