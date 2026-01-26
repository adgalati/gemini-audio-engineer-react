import asyncio
import torch

# Global semaphore to limit concurrent GPU-heavy tasks
# For most consumer GPUs, 1 concurrent task is safest. 
# 2 might be possible on 12GB+ VRAM cards.
MAX_CONCURRENT_HEAVY_JOBS = 1
_heavy_job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_HEAVY_JOBS)

def get_device_info():
    """Returns detailed information about available GPUs."""
    info = {
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else []
    }
    return info

async def run_heavy_task(func, *args, **kwargs):
    """
    Wraps a heavy processing function in a semaphore block.
    """
    async with _heavy_job_semaphore:
        print(f"🚦 Semaphore acquired for heavy task: {func.__name__}")
        # Since stem separation is CPU/GPU intensive and synchronous (subprocess),
        # we run it in a thread to keep the event loop responsive.
        return await asyncio.to_thread(func, *args, **kwargs)
