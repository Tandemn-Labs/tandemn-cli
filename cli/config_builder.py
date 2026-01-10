from typing import Optional
from shared.models.solver import (
    JobConfig, 
    MetaConfig, 
    TaskConfig, 
    ModelConfig, 
    QuantizationConfig,
    FeatureConfig,
    VLLMConfig,
    SLOConfig,
    OfflineSLO,
    PlacementConfig,
)


def build_job_config_from_cli_batched_vllm(
    # Core
    task: str,
    model: str,
    engine: str,
    description: str,
    priority: str,
    # SLO
    slo_mode: str,
    deadline: Optional[int],
    # Placement
    sku: Optional[str],
    # Quantization & Features
    quantization: Optional[str],
    speculative_decode: Optional[bool],
    pd_disaggregation: Optional[bool],
    # vLLM specific
    max_model_len: Optional[int] = None,
    max_num_seqs: Optional[int] = None,
    max_batched_tokens: Optional[int] = None,
    trust_remote_code: bool = True,
    config_format: str = "auto",
    limit_mm: int = 20,
) -> JobConfig:
    
    # Build vLLM config (always build it, transformation will check engine)
    vllm_config = VLLMConfig(
        max_model_len=max_model_len,
        trust_remote_code=trust_remote_code,
        max_num_seqs=max_num_seqs,
        max_num_batched_tokens=max_batched_tokens,
        config_format=config_format,
        limit_mm_per_prompt=limit_mm,
    )
    
    # Build the JobConfig (same structure as Solver output)
    job_config = JobConfig(
        meta=MetaConfig(
            description=description
        ),
        task=TaskConfig(
            type=task,
            priority=priority,
        ),
        model=ModelConfig(
            model_name=model,
            engine=engine,
            quantization=QuantizationConfig(
                bits=quantization
            ),
            features=FeatureConfig(
                speculative_decode=speculative_decode,
                PD_disaggregation=pd_disaggregation,
            ),
            vllm_config=vllm_config,
        ),
        slo=SLOConfig(
            mode=slo_mode,
            offline=OfflineSLO(deadline_hours=deadline) if slo_mode == "offline" else None,
        ),
        placement=PlacementConfig(
            sku_preferences=sku or "not_specified"
        ),
    )
    
    return job_config