from shared.models.login import Cluster, LoginResponse, Session
from shared.models.solver import SolverResponse
import httpx
from typing import Optional, List
from pydantic import ValidationError
from fastapi import HTTPException
import json

# Both central and storage servers are on the same server now
SERVER_BASE_URL = "http://0.0.0.0:26336"

class TandemnAPI:
    def __init__(self, base_url: str = SERVER_BASE_URL) -> None:
        self.base_url = base_url
        self.central_server_url = base_url
        self.storage_server_url = base_url
        self.central_server_client = httpx.AsyncClient(base_url=self.base_url, timeout=200.0)
        self.storage_server_client = httpx.AsyncClient(base_url=self.base_url, timeout=200.0)

    async def presign_upload(self,  remote_path: str, expires: int = 600, user: str = "dummy_user"):
        """
        Get a presigned URL for single-file upload (<500MB).
        """
        response = await self.storage_server_client.post(
            "/storage/presigned_upload",
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

    async def presign_download(self, remote_path: str, user: str = "dummy_user", expires: int = 600):
        """
        Get a presigned URL for downloading a file.
        """
        response = await self.storage_server_client.get(
            "/storage/presigned_download",
            params={"remote_path": remote_path, "user": user, "expires": expires}
        )
        response.raise_for_status()
        return response.json()
    
    async def download_file(self, remote_path: str, local_path: str, user: str = "dummy_user"):
        """
        Download a file using presigned URL.
        """
        # Strip s3:// prefix and bucket, extract only the filename
        if remote_path.startswith("s3://"):
            # s3://bucket/users/user_xxx/filename.txt -> filename.txt
            remote_path = remote_path.split("/")[-1]
        
        # Get presigned URL
        presigned_response = await self.presign_download(remote_path, user)
        download_url = presigned_response.get('url')
        
        # Download using the presigned URL
        async with httpx.AsyncClient(timeout=200.0) as client:
            async with client.stream("GET", download_url) as response:
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

    async def upload_to_presigned_url(self,presigned_response, file_data):
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
        submit_endpoint = "/jobs/submit/batch"
        
        response = await self.central_server_client.post(
            submit_endpoint,
            json=job_config
        )
        response.raise_for_status()
        return response.json()
    

