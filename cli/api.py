from shared.models.login import Cluster, LoginResponse, Session
from shared.models.solver import SolverResponse
import httpx
from typing import Optional, List
from pydantic import ValidationError
from fastapi import HTTPException
import json

# hardcode the ports for now
CENTRAL_SERVER_PORT = 8000
STORAGE_SERVER_PORT = 8001  

class TandemnAPI:
    def __init__(self, central_server_url:str = "https://0.0.0.0:8000", storage_server_url:str = "https://0.0.0.0:8001") -> None: # replace it with the central server location
        self.central_server_url = central_server_url
        self.storage_server_url = storage_server_url
        self.central_server_client = httpx.AsyncClient(base_url=self.central_server_url, timeout=200.0)
        self.storage_server_client = httpx.AsyncClient(base_url=self.storage_server_url, timeout=200.0)

    async def presign_upload(self,  remote_path: str, expires: int = 600, user: str = "dummy_user"):
        """
        Get a presigned URL for single-file upload (<500MB).
        """
        response = await self.storage_server_client.post(
            "/storage/presign/upload",
            data={"remote_path": remote_path, "expires": expires, "user": user}
        )
        response.raise_for_status()
        return response.json()

    async def multipart_start(self, remote_path: str, user: str = "dummy_user"):
        response = await self.storage_server_client.post(
            "/storage/multipart/start",
            data={"remote_path": remote_path, "user": user}
        )
        response.raise_for_status()
        return response.json()

    async def multipart_sign_part(self, upload_id: str, remote_path: str, part_number: int, expires: int = 600, user: str = "dummy_user") -> dict:
        response = await self.storage_server_client.post(
            "/storage/multipart/sign-part",
            data={
                "upload_id": upload_id,
                "remote_path": remote_path,
                "part_number": part_number,
                "expires": expires,
                "user": user
            }
        )
        response.raise_for_status()
        return response.json()

    async def multipart_complete(self, remote_path: str, upload_id: str, parts: List[dict], user: str = "dummy_user"):
        response = await self.storage_server_client.post(
            "/storage/multipart/complete",
            data={
                "remote_path": remote_path,
                "upload_id": upload_id,
                "parts": json.dumps(parts),  # Convert to JSON string
                "user": user
            }
        )
        response.raise_for_status()
        return response.json()

    async def list_files(self, prefix: str = "", user: str = "dummy_user"):
        response = await self.storage_server_client.get(
            f"/storage/list/{user}",
            params={"prefix": prefix}
        )
        response.raise_for_status()
        return response.json()

    async def download_file(self, remote_path: str, local_path: str, user: str = "dummy_user"):
        # Strip s3:// prefix and bucket, extract only the filename
        if remote_path.startswith("s3://"):
            # s3://bucket/users/user_xxx/filename.txt -> filename.txt
            remote_path = remote_path.split("/")[-1]
            
        async with self.storage_server_client.stream("GET",
         f"/storage/download/{user}/{remote_path}"
        ) as response:
            response.raise_for_status()
            with open(local_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
        

    async def delete_file(self, remote_path: str, user: str = "dummy_user"):
        """
        Delete a file from storage.
        """
        # Strip s3:// prefix and bucket, extract only the filename
        if remote_path.startswith("s3://"):
            # s3://bucket/users/user_xxx/filename.txt -> filename.txt
            remote_path = remote_path.split("/")[-1]
            
        response = await self.storage_server_client.delete(
            f"/storage/delete/{user}/{remote_path}"
        )
        response.raise_for_status()
        return response.json()

    async def upload(self,presigned_response, file_data):
        async with httpx.AsyncClient(timeout=200.0) as client:
            response = await client.put(
                presigned_response['url'],
                content=file_data, 
                headers=presigned_response.get('headers', {})
            )
            response.raise_for_status()
    # ============================================================================
    # SOLVER API
    # ============================================================================

    async def submit_solver_prompt(self, prompt: str):
        solver_endpoint = "/jobs/extract"
        
        response = await self.central_server_client.post(
            solver_endpoint,
            json={
                "prompt": prompt
            }
        )
        response.raise_for_status()
        data = response.json()
        
        try:
            validated = SolverResponse(**data)
            return validated.model_dump()
        except ValidationError as e:
            raise RuntimeError(f"Invalid response format: {str(e)}")

    async def submit_job(self, job_config: dict):
        submit_endpoint = "/jobs/submit"
        
        response = await self.central_server_client.post(
            submit_endpoint,
            json=job_config
        )
        response.raise_for_status()
        return response.json()
    

