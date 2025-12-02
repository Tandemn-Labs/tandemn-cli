"""
Minimal Pydantic models for solver API responses.
Mirrors the JobConfig structure from solver/run.py for type validation.
"""

from typing import Literal, Optional, Union
from pydantic import BaseModel


class MetaConfig(BaseModel):
    description: str


class TaskConfig(BaseModel):
    type: Literal["batched_inference", "online_serving", "embeddings", "image_generation"]
    priority: Literal["low", "normal", "high", "urgent"]


class QuantizationConfig(BaseModel):
    method: Literal["none", "int8", "gptq", "awq", "gguf", "a8w8", "w4a8", "not_specified"]
    bits: str  # e.g. "8", "4", "not_specified"


class FeatureConfig(BaseModel):
    speculative_decode: Literal["true", "false", "not_specified"]
    continuous_batching: Literal["true", "false", "not_specified"]
    PD_disaggregation: Literal["true", "false", "not_specified"]


class ModelConfig(BaseModel):
    model_name: Optional[str] = None
    engine: Literal["vllm", "sglang", "diffusers", "xDIT", "not_specified"]
    tokenizer: Literal["huggingface", "mistral", "not_specified"]
    max_context: Union[int, Literal["not_specified"]]
    max_model_len: Union[int, Literal["not_specified"]]
    dtype: Literal["fp32", "bf16", "fp16", "fp8", "fp4", "int8", "int4", "not_specified"]
    quantization: QuantizationConfig
    features: FeatureConfig


class OfflineSLO(BaseModel):
    deadline_hours: Union[int, Literal["not_specified"]]


class SLOConfig(BaseModel):
    mode: Literal["offline", "online"]
    offline: Optional[OfflineSLO] = None


class PlacementConfig(BaseModel):
    sku_preferences: str  # e.g. "H100", "A100", "L40S" or "not_specified"


class JobConfig(BaseModel):
    """Main config structure returned by solver."""
    meta: MetaConfig
    task: TaskConfig
    model: ModelConfig
    slo: SLOConfig
    placement: PlacementConfig


class SolverResponse(BaseModel):
    """Response from solver API endpoint."""
    success: bool
    config: Optional[JobConfig] = None
    error: Optional[str] = None

# class SendToCentralServerRequestBatched(BaseModel):
"""esentially, this just takes the model name and the JobConfig and sends it to the central server"""
#     pass
