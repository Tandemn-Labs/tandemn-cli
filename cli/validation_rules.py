from typing import Literal, Optional, Tuple

ENGINE_TASK_COMPATIBILITY={
    "vllm": ["batched_inference", "online_serving", "embeddings"], # we will mostly remove online inference from vllm in the future
    "sglang": ["batched_inference", "online_serving", "embeddings"],
    "diffusers": ["image_generation"], 
    "xDIT": ["image_generation"],
}

INFERENCE_ENGINES=["vllm","sglang"]
IMAGE_ENGINES=["diffusers","xDIT"]

# Check if engine is compatible or not
def validate_engine_task(engine,task):
    if not engine or not task:
        return False, "Engine and task are required"
    compatible_tasks = ENGINE_TASK_COMPATIBILITY.get(engine)
    if not compatible_tasks:
        return False, f"Engine {engine} is not supported"
    if task not in compatible_tasks:
        return False, f"Task {task} is not supported for engine {engine}"
    return True, None

# check if image + pd_disagg or image+speculative
# both cases are not allowed     
def validate_features_for_task(task,speculative_decode: Optional[bool],pd_disaggregation: Optional[bool]):
    if task=="image_generation":
        if speculative_decode:
            return False, "Speculative decode is not supported for image generation"
        if pd_disaggregation:
            return False, "PD disaggregation is not supported for image generation"
    return True, None

def validate_slo_mode(task, slo_mode: Optional[Literal["offline", "online"]]):
    if not slo_mode:
        return False, "Task and SLO mode are required"
    if task in ["image_generation", "online_serving"] and slo_mode != "online":
        return False, f"Task '{task}' requires SLO mode 'online', got '{slo_mode}'"
    return True, None

def suggest_priority_from_deadline(deadline_hours: Optional[int]):
    if deadline_hours is None:
        return "normal"
    if deadline_hours >= 48:
        return "low"
    elif deadline_hours >= 8:
        return "normal"
    else:
        return "high"

def suggest_engine_for_task(task):
    if task == "image_generation":
        return "diffusers"
    elif task == "batched_inference" or task == "embeddings":
        return "vllm"
    elif task == "online_serving":
        return "sglang"
    return "not_specified"





    