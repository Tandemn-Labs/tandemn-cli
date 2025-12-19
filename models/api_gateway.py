"""
This is the pydantic schema for the cli to send to the api_gateway
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel
from models.solver import QuantizationConfig, JobConfig

class SendToCentralServerRequestBatched(BaseModel):
    """Request to send batched inference job to central server."""
    user_id: str
    selected_file: Optional[str] = None  # S3 path to the file
    # Get some parameters directly from the JobConfig
    description : str
    task_type : str
    task_priority : str
    model_name: Optional[str] = None
    engine: str 
    quantization_bits:str
    is_speculative_decode: str
    is_PD_disaggregation: str
    slo_mode : str
    placement : str
    # Only change the ModelSpecificCofig
    # right now its just vllm, but we can interject the parameters here
    vllm_specific_config: Optional[vLLMSpecificConfig] = None



################## VLLM Specific Config #####################
#### These parameters will be filled both from the LLM parameters and with
# Rules that we will create
 
class SpeculativeConfig(BaseModel):
    method: Optional[Literal["ngram", "suffix", "eagle", "eagle3",  "mlp_speculator", "draft_model", "mtp", "deepseek_mtp", "glm4_moe_mtp", "qwen3_next_mtp", "longcat_flash_mtp"]] = None
    model: Optional[str] = None
    draft_tensor_parallel_size: Optional[int] = 1 # use default for now
    num_speculative_tokens: Optional[int] = None
    max_model_len: Optional[int] = None
    revision: Optional[str] = None
    prompt_lookup_max: Optional[int] = None

class vLLMSpecificConfig(BaseModel):
    # persona 3 config
    max_model_len: int
    trust_remote_code: bool # default is True
    max_num_seqs: int 
    max_num_batched_tokens: int
    config_format: Literal["auto", "mistral"] # use mistral if mistral model is detected
    # persona 2 config
    tokenizer: Optional[str] = None # leave this field blank if not specified (just the path of the tokenizer)
    tokenizer_mode: Optional[Literal["auto","deepseek","mistral"]] = "auto" # Leave this to Auto if not specified
    kv_cache_dtype: Optional[Literal["auto","bfloat16","fp8","fp8_ds_mla","fp8_e4m3","fp8_e5m2","fp8_inc"]] = "auto"
    speculative_config: Optional[SpeculativeConfig] = None
    limit_mm_per_prompt: int # default is 20
    
