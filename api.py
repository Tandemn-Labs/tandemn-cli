from models.login import Cluster, LoginResponse, Session
from models.solver import SolverResponse
import httpx
from typing import Optional, List
from pydantic import ValidationError
from fastapi import HTTPException
import json

class TandemnAPI:
    """
    The ClientSide API that calls the Serverless API Endpoints for 
    Auth
    Storage
    List
    Submit
    NLP_Solver
    Status
    ... and so on other venues for interaction
    This is async and uses httpx
    """

    def __init__(self, base_url:str = "https://api.tandemn.com/api/cli") -> None:
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """
        This is to return the object of the AsyncClient that will be used
        to make the API Calls to the Tandemn API (serverless API)
        """
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=200.0)
        return self._client

    async def aclose(self) -> None:
        """
        Someone closes the terminal, we will shut down the client to avoid any resource leaks
        and to have a graceful shutdown process
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def login(self, api_key:str) -> LoginResponse:
        """
        This sends a post request to the login endpoint (api/cli/login)
        with the API Key in the header and returns the LoginResponse object
        POST /login
        Request: {"ApiKey": api_key}
        Response: {success: ..... youknow} 
        """
        client = await self._get_client()
        print(f"DEBUG: Sending POST to {self.base_url}/login")
        response = await client.post(
            f"{self.base_url}/login", # https://api.tandemn.com/api/cli/login
            json = {"apiKey": api_key}
        )
        print(f"DEBUG: Status Code: {response.status_code}")
        print(f"DEBUG: Response Text: {response.text}")
        data = response.json() # get the response from the api gateway
        if not data["success"] or not response.is_success:
            msg = data["message"] or data["error"] or "Login failed"
            raise RuntimeError(msg)
        # now the login is successful, we have to find what clusters 
        # does the user have access to
        user = data["user"]
        clusters = data.get("clusters", [])
        clusters_list = [
            Cluster(
                id = c["id"],
                name = c["name"],
                description = c.get("description", "")  # Default to empty string if not present
            ) for c in clusters
        ]
        if not clusters_list:
            raise RuntimeError("No clusters found for the user")

        return LoginResponse(
            success = True,
            api_key = api_key,
            user_id = user["id"],
            email = user["email"],
            credits = user["credits"],
            clusters = clusters_list
        )
        # after this login is done, the driver code will save the api_key
        # in the local environment, and then the user can select the cluster 
        # they want to work with


    async def select_cluster(self, api_key:str, cluster_names:List[str]) -> Session:
        """
        This also sends a post request to select the clusters that the user wants to work with
        POST /select-cluster
        Request: {"apiKey": api_key, "clusters": ["Tandemn", "HAL"]}
        Response: {success: ...     you know} 
        """
        client = await self._get_client()
        
        selected_cluster = cluster_names
        if isinstance(cluster_names, list):
            #  selected_cluster = cluster_names[0] if cluster_names else ""
            selected_cluster = cluster_names
        else:
            selected_cluster = [cluster_names]
             
        response = await client.post(
            f"{self.base_url}/select-cluster",
            json = {"apiKey": api_key, "clusters": selected_cluster} # Changed 'clusters' to 'cluster'
        )
        
        data = response.json()
        print("DEBUG: Response Data:", data)
        
        if not data["success"] or not response.is_success:
            msg = data["message"] or data["error"] or "Cluster selection failed"
            return Session(
                success = False,
                message = msg,
                error = data.get("error", None)
            )
        
        # API returns clusters as a list of strings ["Tandemn"]
        cluster_names_from_api = data.get("clusters", [])
        clusters_list = [
             Cluster(id=name, name=name, description="") 
             for name in cluster_names_from_api
        ]

        # Assuming we have selected the correct cluster, we can now return the Session Object
        return Session(
            success = True,
            session_token = data.get("session_token"),  # API uses snake_case
            clusters = clusters_list,
            expires_at = data.get("expires_at"),  # API uses snake_case
            message = data.get("message", None),
            error = data.get("error", None)
        )

    # ============================================================================
    # STORAGE API
    # ============================================================================

    async def presign_upload(self, session_token: str, remote_path: str, expires: int = 600) -> dict:
        """
        Get a presigned URL for single-file upload (<500MB).
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/upload",
            headers={"Authorization": f"Bearer {session_token}"},
            json={"remote_path": remote_path, "expires": expires}
        )
        response.raise_for_status()
        return response.json()

    async def multipart_start(self, session_token: str, remote_path: str) -> dict:
        """
        Start a multipart upload. Returns upload_id.
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/multipart/start",
            headers={"Authorization": f"Bearer {session_token}"},
            json={"remote_path": remote_path}
        )
        response.raise_for_status()
        return response.json()

    async def multipart_sign_part(self, session_token: str, upload_id: str, remote_path: str, part_number: int, expires: int = 600) -> dict:
        """
        Get a presigned URL for a specific part.
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/multipart/sign-part",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "upload_id": upload_id,
                "remote_path": remote_path,
                "part_number": part_number,
                "expires": expires
            }
        )
        response.raise_for_status()
        return response.json()

    async def multipart_complete(self, session_token: str, remote_path: str, upload_id: str, parts: List[dict]) -> dict:
        """
        Complete a multipart upload.
        """

        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/multipart/complete",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "remote_path": remote_path,
                "upload_id": upload_id,
                "parts": parts
            }
        )
        response.raise_for_status()
        return response.json()

    async def list_files(self, session_token: str, prefix: str = "") -> dict:
        """
        List all files for a user.
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/list",
            headers={"Authorization": f"Bearer {session_token}"},
            params={"prefix": prefix}
        )
        response.raise_for_status()
        return response.json()

    async def download_file(self, session_token: str, remote_path: str, local_path: str) -> None:
        """
        Download a file from storage.
        """
        # Strip s3:// prefix and bucket, extract only the filename
        if remote_path.startswith("s3://"):
            # s3://bucket/users/user_xxx/filename.txt -> filename.txt
            remote_path = remote_path.split("/")[-1]
            
        client = await self._get_client()
        async with client.stream("GET",
         f"{self.base_url}/download",
        headers={"Authorization": f"Bearer {session_token}"},
        params={"remote_path": remote_path}
        ) as response:
            response.raise_for_status()
            with open(local_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

    async def delete_file(self, session_token: str, remote_path: str) -> dict:
        """
        Delete a file from storage.
        """
        # Strip s3:// prefix and bucket, extract only the filename
        if remote_path.startswith("s3://"):
            # s3://bucket/users/user_xxx/filename.txt -> filename.txt
            remote_path = remote_path.split("/")[-1]
            
        client = await self._get_client()
        response = await client.delete(
            f"{self.base_url}/delete",
            headers={"Authorization": f"Bearer {session_token}"},
            params={"remote_path": remote_path}
        )
        response.raise_for_status()
        return response.json()

    # ============================================================================
    # SOLVER API
    # ============================================================================

    async def submit_solver_prompt(self, prompt: str, session_token: str) -> dict:
        """
        Submit a natural language prompt to the solver API.
        The solver will process the prompt using GPT and return a structured config.
        
        Args:
            prompt: Natural language description of the job requirements (max 500 chars)
            session_token: The session token from select_cluster response
            
        Returns:
            dict: Structured job configuration from the solver
            
        Example response:
        {
            "success": true,
            "config": {
                "meta": {"description": "..."},
                "task": {"type": "batched_inference", "priority": "normal"},
                "model": {...},
                "slo": {...},
                "placement": {...}
            }
        }
        """
        client = await self._get_client()
        
        solver_endpoint = f"{self.base_url}/jobs/extract"
        
        response = await client.post(
            solver_endpoint,
            headers={
                "Authorization": f"Bearer {session_token}"
            },
            json={
                "prompt": prompt
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Validate response structure
        try:
            validated = SolverResponse(**data)
            return validated.model_dump()
        except ValidationError as e:
            raise RuntimeError(f"Invalid response format: {str(e)}")

    async def submit_job(self, session_token: str, job_config: dict) -> dict:
        """
        Submit a job to the Tandemn orchestrator.
        
        Args:
            session_token: The session token from select_cluster response
            job_config: Dictionary containing job configuration with fields like:
                - task_mode: str (e.g., "batched_inference")
                - model_name: str (e.g., "llama-70b-hf")
                - backend: str (e.g., "vllm")
                - quantization: str (e.g., "awq")
                - dataset_path: str (e.g., "s3://...")
                - column_names: list (e.g., ["prompt", "response"])
                - slo: str (e.g., "2h")
                - generation_kwargs: dict (optional)
                
        Returns:
            dict: Job submission response
            
        Example response:
        {
            "status": "success",
            "job_id": "uuid-here",
            "message": "Job {job_id} submitted successfully",
            "application_queue_key": "tandemn:app_jobs:llama-70b-hf:batched_inference:vllm:awq"
        }
        """
        client = await self._get_client()
        
        submit_endpoint = f"{self.base_url}/jobs/submit"
        
        response = await client.post(
            submit_endpoint,
            headers={
                "Authorization": f"Bearer {session_token}"
            },
            json=job_config
        )
        response.raise_for_status()
        return response.json()
    

