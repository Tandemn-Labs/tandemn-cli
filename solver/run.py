from typing import List, Literal, Union, Optional
from pydantic import BaseModel
from openai import OpenAI
import json


client = OpenAI()

# =========================
# Pydantic Schemas
# =========================

class MetaConfig(BaseModel):
    # A short description (about 20 characters) of the job
    description: str


class TaskConfig(BaseModel):
    # type: batched_inference | online_serving | embeddings | image_generation
    type: Literal["batched_inference", "online_serving", "embeddings", "image_generation"]
    # priority: low | normal | high | urgent
    priority: Literal["low", "normal", "high", "urgent"]


class QuantizationConfig(BaseModel):
    # method: none | int8 | gptq | awq | gguf | a8w8 | w4a8 | not_specified
    method: Literal["none", "int8", "gptq", "awq", "gguf", "a8w8", "w4a8", "not_specified"]
    # bits: string so we can also support "not_specified"
    bits: str  # e.g. "8", "4", "not_specified"


class FeatureConfig(BaseModel):
    # true | false | not_specified
    speculative_decode: Literal["true", "false", "not_specified"]
    continuous_batching: Literal["true", "false", "not_specified"]
    PD_disaggregation: Literal["true", "false", "not_specified"]


class ModelConfig(BaseModel):
    model_name: Optional[str] = None
    # engine: vllm | sglang | diffusers | xDIT | not_specified
    engine: Literal["vllm", "sglang", "diffusers", "xDIT", "not_specified"]
    # tokenizer: huggingface | mistral | not_specified
    tokenizer: Literal["huggingface", "mistral", "not_specified"]
    # int or "not_specified"
    max_context: Union[int, Literal["not_specified"]]
    max_model_len: Union[int, Literal["not_specified"]]
    # dtype: fp32 | bf16 | fp16 | fp8 | fp4 | int8 | int4 | not_specified
    dtype: Literal["fp32", "bf16", "fp16", "fp8", "fp4", "int8", "int4", "not_specified"]
    quantization: QuantizationConfig
    features: FeatureConfig


class OfflineSLO(BaseModel):
    # deadline_hours: required for batched_inference
    # Use "not_specified" if not told.
    deadline_hours: Union[int, Literal["not_specified"]]


class SLOConfig(BaseModel):
    # mode: offline | online (ALWAYS online for image_generation)
    mode: Literal["offline", "online"]
    offline: Optional[OfflineSLO] = None


class PlacementConfig(BaseModel):
    # sku_preferences: GPU type or "not_specified"
    sku_preferences: str


class JobConfig(BaseModel):
    meta: MetaConfig
    task: TaskConfig
    model: ModelConfig
    slo: SLOConfig
    placement: PlacementConfig


# =========================
# System Prompt
# =========================

SYSTEM_PROMPT = """
You are an information extractor that fills a structured config (CFG) from user text.

Your ONLY job is to extract values for the following config schema from what the user says.
Do NOT give suggestions, do NOT infer business logic beyond what is clearly described in the text.
If something is not explicitly specified, use the exact sentinel values specified below.

CONFIG SHAPE (for reference):

meta:
  description: # [type:str] A short description in ~20 characters of the job

task:
  type:    # [type:str] Options: batched_inference | online_serving | embeddings | image_generation
  priority: # [type:str] low | normal | high | urgent
            # (anything online is urgent. rest classify based on hours:
            # >= 48hr => low, 24–8hr => normal, <8hr => high)
            # 48hr is low, 24-8 hr is normal, anything less than 8 is high

model:
  model_name: ____   # [type:str] The name of the model to use. This should be not_specified for batched_inference. 
  But for others, do take in the model name.
  engine: ____      # [type:str] vllm | sglang | diffusers | xDIT | not_specified
  tokenizer: ____   # [type:str] huggingface | mistral | not_specified
  max_context: ____ # [type:int] Put "not_specified" if not told
  max_model_len: ____ # [type:int] Put "not_specified" if not told
  dtype: ____       # [type:str] fp32 | bf16 | fp16 | fp8 | fp4 | int8 | int4 | not_specified
  quantization:
    method: ____    # [type:str] none | int8 | gptq | awq | gguf | a8w8 | w4a8 | not_specified
    bits: ____      # [type:str] if applicable, else "not_specified"
  features:
    speculative_decode:   # [type:str] true | false | not_specified
    continuous_batching:  # [type:str] true | false | not_specified
    PD_disaggregation:    # [type:str] true | false | not_specified

slo:
  mode: ____        # [type:str] offline | online
                    # It is ALWAYS "online" for image_generation
  offline:
    deadline_hours: ____  # [type:int] required for batched_inference;
                          # use "not_specified" if not told.

placement:
  sku_preferences: ____   # [type:str] e.g. "H100", "A100", "L40S" or "not_specified"

INSTRUCTION DETAILS:

1. Follow the allowed OPTIONS exactly (case-sensitive).
2. If the user does NOT specify a field:
   - For engine/tokenizer/dtype/features/quantization/mode/sku_preferences:
     use "not_specified" where that is an allowed option.
   - For numeric fields that allow "not_specified", return either an integer
     or the exact string "not_specified".
3. Infer:
   - task.type from phrases like "batched", "offline job", "online service", "embeddings",
     "image generation", etc.
   - slo.mode: "online" for online_serving or image_generation; "offline" for batched_inference
     and clearly offline batch jobs.
   - task.priority from the deadline:
       * If slo.mode is "online" => "urgent"
       * If offline and deadline_hours >= 48 => "low"
       * If 24 <= deadline_hours < 48 or 8 <= deadline_hours < 24 => "normal"
       * If deadline_hours < 8 => "high"
     If no deadline is given, use "normal" for offline.
4. DO NOT invent engines, dtypes, quantization methods, features, or SKUs
   if they are not mentioned. Use "not_specified" in that case.
5. Your output MUST be a valid instance of the JobConfig schema.
6. If the user mentions a model name, use it in the model_name field, but use not_specified 
when the case is batched_inference.
Do not add extra keys or text.
"""


# =========================
# Example Usage
# =========================

if __name__ == "__main__":
    # Example user_input prompts to test SYSTEM_PROMPT
    test_prompts = [
        """I want to run Batched Inference on my file my_file.jsonl
        and I want to make sure that it can return me the results in 10 hours
        and also I want to specify that the quantization needs to be AWQ 
        for this particular model that too int8 and not lower than that. 
        Oh and please not use vLLM, use just SGLang.""",
        # Placeholder 2: Online serving
        """Please set up an online service for embeddings endpoint, using Qwen/Qwen3-Embedding-8B, use the model name
        I need p99 latency and can run on any GPU. Use bf16 if possible.""",
        # Placeholder 3: Image generation
        """Set up image generation using diffusers, for the wavespeed-ai/flux-kontext-dev model on a single H100.
        Make sure the model is of full precision and not quantized. Please use the framework as diffusers.""",
        # Placeholder 4: Missing fields
        """Bhai mere pas ek jsonl file hai, wo mere local disk pe padi hai, usme kuch promopts hai chalane hai 
        result mujhe 2 ghante me chahiye, Need to give it to the boss.""",
        # Placeholder 5: Specific tokenizer and deadline
        """I have some prompts kept in a files and I need to run them for a model distillation task. It must use mistral tokenizer,
         has to complete in less than 5 hours, and I'm ok with quantization method being awq and bits to be 8."""]
    

    for idx, user_input in enumerate(test_prompts):
        print(f"\n=== Test Prompt {idx+1} ===")
        response = client.responses.parse(
            model="gpt-5-nano",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            text_format=JobConfig,
        )

        config: JobConfig = response.output_parsed
        print("\033[1;34m" + "User Input:" + "\033[0m")
        print(f"{user_input.strip()}\n")
        
        print("\033[1;32m" + "Generated Config:" + "\033[0m")
        print(json.dumps(config.model_dump(), indent=2, ensure_ascii=False))

