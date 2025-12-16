from typing import List, Literal, Union, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import uvicorn
from solver import JobConfig

# =========================
# System Prompt
# =========================

with open("PROMPT.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# =========================
# FastAPI Server
# =========================

app = FastAPI(
    title="Tandemn Solver Prompt Test API",
)

client = OpenAI()

class PromptRequest(BaseModel):
    prompt: str

class PromptResponse(BaseModel):
    config: dict

@app.post("/extract", response_model=PromptResponse)
async def extract_job_config(payload: PromptRequest):
    user_input = payload.prompt

    try:
        response = client.responses.parse(
            model="gpt-5-nano",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            text_format=JobConfig,
        )
        config: JobConfig = response.output_parsed
        print(config)
        return JSONResponse(content={"success": True, "config": config.model_dump()})    
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)})
# Optional: enable running server with python run.py
if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)

# run this file outside solver with python -m solver.run