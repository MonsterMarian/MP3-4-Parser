from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import asyncio
import os
from splitter_core import SplitterCore

app = FastAPI(title="Marian's Splitter API")

# Setup CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

core = SplitterCore()

class SplitRequest(BaseModel):
    input_file: str
    output_dir: str
    num_parts: int = 2
    overlap: float = 5.0

@app.post("/api/split")
async def start_split(req: SplitRequest):
    if core.is_running:
        raise HTTPException(status_code=400, detail="Proces již běží.")
    
    if not os.path.exists(req.input_file):
        raise HTTPException(status_code=400, detail="Vstupní soubor neexistuje.")
    
    if not os.path.exists(req.output_dir):
        # Pokus o vytvoření složky
        try:
            os.makedirs(req.output_dir, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Nelze vytvořit výstupní složku: {str(e)}")

    if req.num_parts < 2:
        raise HTTPException(status_code=400, detail="Počet částí musí být alespoň 2.")

    # Vyčistíme staré logy
    while not core.log_queue.empty():
        try:
            core.log_queue.get_nowait()
        except Exception:
            pass

    core.start_split(req.input_file, req.output_dir, req.num_parts, req.overlap)
    return {"message": "Proces spuštěn"}

@app.post("/api/cancel")
async def cancel_split():
    if not core.is_running:
        return {"message": "Nic neběží."}
    
    core.cancel()
    return {"message": "Proces byl zrušen."}

@app.get("/api/status")
async def status_stream(request: Request):
    async def event_generator():
        # First yield current status immediately
        yield {
            "event": "status",
            "data": f'{{"status": "{core.status}", "progress": {core.progress}}}'
        }
        
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            # Check queue for new logs/status
            try:
                # We use block=False and a short sleep to allow checking is_disconnected
                msg = core.log_queue.get(block=False)
                if msg["type"] == "log":
                    yield {
                        "event": "log",
                        "data": f'{{"message": "{msg["message"]}"}}'
                    }
                elif msg["type"] == "status":
                    yield {
                        "event": "status",
                        "data": f'{{"status": "{msg["status"]}", "progress": {msg["progress"]}}}'
                    }
                elif msg["type"] == "done":
                    yield {
                        "event": "done",
                        "data": "{}"
                    }
                elif msg["type"] == "error":
                    yield {
                        "event": "error",
                        "data": f'{{"message": "{msg["message"]}"}}'
                    }
            except Exception:
                await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
