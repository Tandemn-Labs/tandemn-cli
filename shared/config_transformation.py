from shared.models.api_gateway import BatchedRequest, vLLMSpecificConfig, SpeculativeConfig, OnlineServingRequest
from shared.models.solver import JobConfig
import requests
from typing import Optional, Union

def get_config_from_hf(model_name: str):
    config_url=f"https://huggingface.co/{model_name}/raw/main/config.json"
    response = requests.get(config_url)
    config = response.json()
    if response.status_code == 200:
        return config
    else:
        raise Exception(f"Failed to get config from Hugging Face: {response.status_code}")

def detect_model_family_from_config(config):
    architectures = config.get("architectures", [])
    if not architectures:
        return "unknown"
    arch = architectures[0].lower()
    model_type = config.get("model_type", "").lower()
    if "deepseek" in arch:
        if "v3" in model_type or "v32" in model_type:
            return "deepseek_v3"
        return "deepseek"
    if "glm" in arch or "chatglm" in arch:
        return "glm4_moe"
    if "qwen" in arch:
        if "qwen3" in model_type and "next" in model_type:
            return "qwen3_next"
        return "qwen"
    if "longcat" in arch:
        return "longcat_flash"
    if "llama" in arch:
        return "llama"
    if "gpt" in arch:
        return "gpt_oss"
    if "mistral" in arch:
        return "mistral"
    
    return "unknown"

    
def get_compatible_mtp_method(model_family: str):
    mtp_mapping = {
        "deepseek_v3": "mtp",
        "glm4_moe": "glm4_moe_mtp",
        "qwen3_next": "qwen3_next_mtp",
        "longcat_flash": "longcat_flash_mtp",
    }
    return mtp_mapping.get(model_family)

def convert_to_central_server_config(JobConfig: JobConfig,
    user_id: str,
    input_file: Optional[str] = None,
    output_file: Optional[str] = None,
    num_lines: Optional[int] = None,
    ):
    """
    this is to take all the inputs of the job_config, 
    welcome screen and then validate it, and then send it
    to the central server.
    """
    # start building the central server config
    # take in the job config and construct the SendToCentralServerRequestBatched object
    # then we add stuff to modelSpecificConfig

    # Step 1 - Build the SendToCentralServerRequestBatched object
    if JobConfig.task.type == "batched_inference":
        central_server_config = BatchedRequest(
                                user_id=user_id,
                                description=JobConfig.meta.description,
                                task_type=JobConfig.task.type,
                                task_priority=JobConfig.task.priority,
                                model_name=JobConfig.model.model_name,
                                engine=JobConfig.model.engine,
                                quantization_bits=JobConfig.model.quantization.bits,
                                is_speculative_decode=JobConfig.model.features.speculative_decode,
                                is_PD_disaggregation=JobConfig.model.features.PD_disaggregation,
                                slo_mode=JobConfig.slo.mode,
                                slo_deadline_hours=JobConfig.slo.offline.deadline_hours,
                                placement=JobConfig.placement.sku_preferences,
                                num_lines=num_lines)
    elif JobConfig.task.type == "online_serving":
        central_server_config = OnlineServingRequest(
                                user_id=user_id,
                                description=JobConfig.meta.description,
                                task_type=JobConfig.task.type,
                                task_priority=JobConfig.task.priority,
                                model_name=JobConfig.model.model_name,
                                engine=JobConfig.model.engine,
                                quantization_bits=JobConfig.model.quantization.bits,
                                is_speculative_decode=JobConfig.model.features.speculative_decode,
                                is_PD_disaggregation=JobConfig.model.features.PD_disaggregation,
                                slo_mode=JobConfig.slo.mode,
                                placement=JobConfig.placement.sku_preferences)
    else:
        raise ValueError(f"Invalid task type: {JobConfig.task.type}")
    if JobConfig.task.type == "batched_inference" and (input_file or output_file):
        central_server_config.input_file = input_file
        central_server_config.output_file = output_file
    # Step 2 - check if we can even get the config from the huggingface
    config = get_config_from_hf(central_server_config.model_name)
    if config is None:
        raise Exception(f"Failed to get config from Hugging Face, please check if the model exists")
    # Step 3 - Find Quantization Method for this Model
    quantization_provided_by_user = JobConfig.model.quantization.bits
    if JobConfig.model.quantization.bits is not None:
        try: 
            quantization_config = config.get("quantization_config", None)
            # check if the quantization is BNB? If yes, accept and forward as is
            # also check if the precision is the same as the one provided by the user?
            if quantization_config and quantization_config.get("quant_method") == "bitsandbytes":
                is_4_byte = quantization_config.get("bnb_4bit_quant_type", None)
                is_8_byte = quantization_config.get("bnb_8bit_quant_type", None)
                if is_4_byte:
                    quantization_precision = '4'
                elif is_8_byte:
                    quantization_precision = '8'
                else:
                    #trust the user 
                    quantization_precision = quantization_provided_by_user
            else:
                # Use what the user specified
                quantization_precision = quantization_provided_by_user
            # change the quantization_bits in the central server config
            central_server_config.quantization_bits = quantization_precision
        except Exception as e:
            raise Exception("Failed to get quantization config")
    # vllm will automatically get the quantization method
    # step 4 - Set the vLLM parameters
    if JobConfig.model.engine == "vllm":
        vllm_config = vLLMSpecificConfig(
            max_model_len=JobConfig.model.vllm_config.max_model_len,
            trust_remote_code=JobConfig.model.vllm_config.trust_remote_code,
            max_num_seqs=JobConfig.model.vllm_config.max_num_seqs,
            max_num_batched_tokens=JobConfig.model.vllm_config.max_num_batched_tokens,
            config_format=JobConfig.model.vllm_config.config_format,
            limit_mm_per_prompt=JobConfig.model.vllm_config.limit_mm_per_prompt,
        )
        # step 5 - Combine everything
        central_server_config.vllm_specific_config = vllm_config

        # step 6 - Apply Good Defaults for Speculative Decoding
        central_server_config = good_defaults(central_server_config, config)
    return central_server_config


def good_defaults(central_config: Union[BatchedRequest, OnlineServingRequest], model_config: dict):
    if central_config.is_speculative_decode != True:
        return central_config
    ########################################################
    # Step 1 - Get good defaults for Speculative Decoding 
    model_family = detect_model_family_from_config(model_config)
    
    # Try MTP methods 
    mtp_method = get_compatible_mtp_method(model_family)
    if mtp_method:
        central_config.vllm_specific_config.speculative_config = SpeculativeConfig(
            method=mtp_method,
            num_speculative_tokens=5 # a good default
        )
        return central_config
    
    # # Try Eagle for supported families (but needs draft_model, so skip for now)
    # eagle_supported = ["llama", "qwen", "gpt_oss"]
    # if model_family in eagle_supported:
    #     pass
    
    # Fallback to ngram (works for all models)
    central_config.vllm_specific_config.speculative_config = SpeculativeConfig(
        method="ngram",
        num_speculative_tokens=3,
        prompt_lookup_max=10
    )
    ########################################################
    # Step 2 - Get good defaults for every "not_specified" parameter
    if central_config.vllm_specific_config.tokenizer == "not_specified":
        central_config.vllm_specific_config.tokenizer = None
    if central_config.vllm_specific_config.tokenizer_mode in (None, "not_specified"):
        central_config.vllm_specific_config.tokenizer_mode = "auto"
    if central_config.vllm_specific_config.kv_cache_dtype in (None, "not_specified"):
        central_config.vllm_specific_config.kv_cache_dtype = "auto"
    if central_config.vllm_specific_config.limit_mm_per_prompt in (None, "not_specified"):
        central_config.vllm_specific_config.limit_mm_per_prompt = 20
    
    return central_config



