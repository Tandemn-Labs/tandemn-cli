from models.login import Cluster, LoginResponse, Session
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
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=20.0)
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
