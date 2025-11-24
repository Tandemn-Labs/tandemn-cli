from models.login import Cluster, LoginResponse, Session
from models.solver import SolverResponse
import httpx
from typing import Optional, List

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
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
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
                description = c["description"]
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
        
        # If it's a list, take the first one for now to satisfy the 'cluster' field requirement
        # If it's a string, just use it.
        selected_cluster = cluster_names
        if isinstance(cluster_names, list):
             selected_cluster = cluster_names[0] if cluster_names else ""
             
        response = await client.post(
            f"{self.base_url}/select-cluster",
            json = {"apiKey": api_key, "cluster": selected_cluster} # Changed 'clusters' to 'cluster'
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
        cluster_val = data.get("cluster")
        clusters_list = [
             Cluster(id=cluster_val, name=cluster_val, description="") 
        ] if cluster_val else []


        # Assuming we have selected the correct cluster, we can now return the Session Object
        return Session(
            success = True,
            session_token = data.get("sessionToken"),  # API uses camelCase
            clusters = clusters_list,
            expires_at = data.get("expiresAt"),  # API uses camelCase
            message = data.get("message", None),
            error = data.get("error", None)
        )

    # ============================================================================
    # STORAGE API
    # ============================================================================

    async def presign_upload(self, remote_path: str, user: str, expires: int = 600) -> dict:
        """
        Get a presigned URL for single-file upload (<500MB).
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/storage/presign/upload",
            data={"remote_path": remote_path,"user": user, "expires": expires}
        )
        response.raise_for_status()
        return response.json()

    async def multipart_start(self, remote_path: str, user: str) -> dict:
        """
        Start a multipart upload. Returns upload_id.
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/storage/multipart/start",
            data={"remote_path": remote_path, "user": user}
        )
        response.raise_for_status()
        return response.json()

    async def multipart_sign_part(self, upload_id: str, user: str, remote_path: str, part_number: int, expires: int = 600) -> dict:
        """
        Get a presigned URL for a specific part.
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/storage/multipart/sign-part",
            data={
                "upload_id": upload_id,
                "user": user,
                "remote_path": remote_path,
                "part_number": part_number,
                "expires": expires
            }
        )
        response.raise_for_status()
        return response.json()

    async def multipart_complete(self, user: str, remote_path: str, upload_id: str, parts: List[dict]) -> dict:
        """
        Complete a multipart upload.
        """
        import json
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/storage/multipart/complete",
            data={
                "user": user,
                "remote_path": remote_path,
                "upload_id": upload_id,
                "parts": json.dumps(parts)
            }
        )
        response.raise_for_status()
        return response.json()

    async def list_files(self, user: str, prefix: str = "") -> dict:
        """
        List all files for a user.
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/storage/list/{user}",
            params={"prefix": prefix}
        )
        response.raise_for_status()
        return response.json()

    async def download_file(self, user: str, remote_path: str, local_path: str) -> None:
        """
        Download a file from storage.
        """
        # Strip s3:// prefix and bucket, extract only the filename
        if remote_path.startswith("s3://"):
            # s3://bucket/users/user_xxx/filename.txt -> filename.txt
            remote_path = remote_path.split("/")[-1]
            
        client = await self._get_client()
        async with client.stream("GET", f"{self.base_url}/storage/download/{user}/{remote_path}") as response:
            response.raise_for_status()
            with open(local_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

    async def delete_file(self, user: str, remote_path: str) -> dict:
        """
        Delete a file from storage.
        """
        # Strip s3:// prefix and bucket, extract only the filename
        if remote_path.startswith("s3://"):
            # s3://bucket/users/user_xxx/filename.txt -> filename.txt
            remote_path = remote_path.split("/")[-1]
            
        client = await self._get_client()
        response = await client.delete(f"{self.base_url}/storage/delete/{user}/{remote_path}")
        response.raise_for_status()
        return response.json()

    # ============================================================================
    # SOLVER API
    # ============================================================================

    async def submit_solver_prompt(self, prompt: str, user_id: str) -> dict:
        """
        Submit a natural language prompt to the solver API.
        The solver will process the prompt using GPT and return a structured config.
        
        Args:
            prompt: Natural language description of the job requirements (max 500 chars)
            user_id: The user ID from the session
            
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
        
        # TODO: Replace with actual solver endpoint URL when ready
        solver_endpoint = "http://0.0.0.0:8000/extract"
        
        response = await client.post(
            solver_endpoint,
            json={
                "prompt": prompt,
                "user_id": user_id
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Validate response structure
        try:
            validated = SolverResponse(**data)
            return validated.model_dump()
        except Exception as e:
            # If validation fails, return error response
            return {
                "success": False,
                "error": f"Invalid response format: {str(e)}",
                "config": None
            }


