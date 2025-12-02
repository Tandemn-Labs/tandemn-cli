from typing import List, Literal, Union, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import uvicorn
from models.solver import JobConfig

# # =========================
# # Pydantic Schemas
# # =========================

# class MetaConfig(BaseModel):
#     # A short description (about 20 characters) of the job
#     description: str


# class TaskConfig(BaseModel):
#     # type: batched_inference | online_serving | embeddings | image_generation
#     type: Literal["batched_inference", "online_serving", "embeddings", "image_generation"]
#     # priority: low | normal | high | urgent
#     priority: Literal["low", "normal", "high", "urgent"]


# class QuantizationConfig(BaseModel):
#     # method: none | int8 | gptq | awq | gguf | a8w8 | w4a8 | not_specified
#     method: Literal["none", "int8", "gptq", "awq", "gguf", "a8w8", "w4a8", "not_specified"]
#     # bits: string so we can also support "not_specified"
#     bits: str  # e.g. "8", "4", "not_specified"


# class FeatureConfig(BaseModel):
#     # true | false | not_specified
#     speculative_decode: Literal["true", "false", "not_specified"]
#     continuous_batching: Literal["true", "false", "not_specified"]
#     PD_disaggregation: Literal["true", "false", "not_specified"]


# class ModelConfig(BaseModel):
#     model_name: Optional[str] = None
#     # engine: vllm | sglang | diffusers | xDIT | not_specified
#     engine: Literal["vllm", "sglang", "diffusers", "xDIT", "not_specified"]
#     # tokenizer: huggingface | mistral | not_specified
#     tokenizer: Literal["huggingface", "mistral", "not_specified"]
#     # int or "not_specified"
#     max_context: Union[int, Literal["not_specified"]]
#     max_model_len: Union[int, Literal["not_specified"]]
#     # dtype: fp32 | bf16 | fp16 | fp8 | fp4 | int8 | int4 | not_specified
#     dtype: Literal["fp32", "bf16", "fp16", "fp8", "fp4", "int8", "int4", "not_specified"]
#     quantization: QuantizationConfig
#     features: FeatureConfig


# class OfflineSLO(BaseModel):
#     # deadline_hours: required for batched_inference
#     # Use "not_specified" if not told.
#     deadline_hours: Union[int, Literal["not_specified"]]


# class SLOConfig(BaseModel):
#     # mode: offline | online (ALWAYS online for image_generation)
#     mode: Literal["offline", "online"]
#     offline: Optional[OfflineSLO] = None


# class PlacementConfig(BaseModel):
#     # sku_preferences: GPU type or "not_specified"
#     sku_preferences: str


# class JobConfig(BaseModel):
#     meta: MetaConfig
#     task: TaskConfig
#     model: ModelConfig
#     slo: SLOConfig
#     placement: PlacementConfig


# =========================
# System Prompt
# =========================

with open("solver/PROMPT.txt", "r", encoding="utf-8") as f:
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