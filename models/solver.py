"""
Minimal Pydantic models for solver API responses.
Mirrors the JobConfig structure from solver/run.py for type validation.
"""

from typing import Literal, Optional, Union
from pydantic import BaseModel


### Below Classes for LLM to fill###############
#### Description Configuration ##
class MetaConfig(BaseModel):
    description: str
#################################

## Task specific configuration ##
class TaskConfig(BaseModel):    
    type: Literal["batched_inference", "online_serving", "embeddings", "image_generation"]
    priority: Literal["low", "normal", "high", "urgent"]
#################################

## Model Specific Configurations ##
class QuantizationConfig(BaseModel):
    bits: str  # e.g. "8", "4", "not_specified"

class FeatureConfig(BaseModel):
    speculative_decode: Optional[bool] = None
    PD_disaggregation: Optional[bool] = None

class VLLMConfig(BaseModel):
    max_model_len: Optional[int] = None
    trust_remote_code: Optional[bool] = None
    max_num_seqs: Optional[int] = None
    max_num_batched_tokens: Optional[int] = None
    config_format: Optional[Literal["auto", "mistral"]] = None
    limit_mm_per_prompt: Optional[int] = None

class ModelConfig(BaseModel):
    model_name: Optional[str] = None
    engine: Literal["vllm", "sglang", "diffusers", "xDIT", "not_specified"]
    quantization: QuantizationConfig
    features: FeatureConfig
    vllm_config: VLLMConfig
    # ----- sglang_specific_config: SGLangSpecificConfig ----
    # ----- diffusers_specific_config: DiffusersSpecificConfig ----
    # ----- xDIT_specific_config: XDITSpecificConfig ----


####################################

## SLO specific configuration ##
class OfflineSLO(BaseModel):
    deadline_hours: Union[int, Literal["not_specified"]]

class SLOConfig(BaseModel):
    mode: Literal["offline", "online"]
    offline: Optional[OfflineSLO] = None
    # online : ----- to be added later ------
#################################

## Placement specific configuration ##
class PlacementConfig(BaseModel):
    sku_preferences: str  # e.g. "H100", "A100", "L40S" or "not_specified"
#################################

## Culmination of all these specific configurations ##
class JobConfig(BaseModel):
    """Main config structure returned by solver."""
    meta: MetaConfig
    task: TaskConfig
    model: ModelConfig
    slo: SLOConfig
    placement: PlacementConfig
#################################

class SolverResponse(BaseModel):
    """Response from solver API endpoint."""
    success: bool
    config: Optional[JobConfig] = None
    error: Optional[str] = None


