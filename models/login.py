from dataclasses import dataclass
from typing import List, Optional 


@dataclass
class Cluster:
    """
    This dataclass is used for storing the information from the user,
    when the user wants to specify the cluster that they wanna work on.
    The data stored here PROBABLY will also be stored in some sort of an
    environment variable, so that once the user checks it, they dont have to
    re-specify it again and again
    """
    id:str
    name:str
    description:str # not sure if needed

@dataclass
class LoginResponse:
    """
    This is the response that we get after we call the login endpoint( api/cli/login)
    The response looks something like this - 
    {"success":true,
    "user":{"id":
    "user_35FaA58QpJxiRZvf9yJwfSMAajr",
    "email":"ibuyy@illinois.edu",
    "credits":20.999815732},
    "clusters":[{"id":"Tandemn","name":"Tandemn","description":"Main Tandemn cluster - available to all users"}]}
    So, we need to store the data in a way that is easy to access and use.
    If there is no user that exists, then we get the response as - 
    {"success":false,"error":"Invalid API key","message":"The provided API key is invalid or has been deactivated"}
    """
    success:bool
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    credits: Optional[float] = None 
    clusters: Optional[List[Cluster]] = None
    # these two are present in the response when the user/API key is not found
    error: Optional[str] = None
    message: Optional[str] = None

@dataclass
class Session:
    """
    This is the session that GETS SELECTED by the user. There are two cases of it-
    When the user logs in and is provided with the choice of cluster they wanna select. 
    or 
    When the user has already made that choice, and we store it in an environment variable, 
    and the user opens another terminal, so it gets called again
    """
    success:bool
    session_token: Optional[str] = None
    clusters: Optional[List[Cluster]] = None
    expires_at: Optional[str] = None
    # these two are present in the response when the user/API key is not found
    message: Optional[str] = None
    error: Optional[str] = None



    
