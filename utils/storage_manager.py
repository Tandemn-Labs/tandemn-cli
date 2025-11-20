import asyncio
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
import httpx
from api import TandemnAPI
import logging
# Constants
CHUNK_SIZE = 64 * 1024 * 1024  # 64MB chunks for multipart
MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100MB

class UploadTask:
    def __init__(self, file_path: Path, user_id: str, remote_path: str):
        self.file_path = file_path
        self.user_id = user_id
        self.remote_path = remote_path
        self.size = file_path.stat().st_size
        self.status = "pending" # pending, uploading, paused, completed, error
        self.progress = 0.0
        self.uploaded_bytes = 0
        self.upload_id = None # For multipart
        self.parts = [] 
        self.error = None
        self.created_at = time.time()

    def to_dict(self):
        return {
            "file_path": str(self.file_path),
            "remote_path": self.remote_path,
            "size": self.size,
            "status": self.status,
            "progress": self.progress,
            "uploaded_bytes": self.uploaded_bytes,
            "upload_id": self.upload_id,
            "error": self.error
        }

class UploadManager:
    _instance = None
    STATE_FILE = Path(os.getenv("TEMP", "/tmp")) / "tandemn_upload_state.json"

    def __new__(cls, api: TandemnAPI = None):
        if cls._instance is None:
            cls._instance = super(UploadManager, cls).__new__(cls)
            cls._instance.api = api
            cls._instance.queue = []
            cls._instance.active_tasks = []
            cls._instance.running = False
            cls._instance.history = []
            cls._instance.callback = None  # For UI updates
            cls._instance._load_state()
        return cls._instance

    def set_api(self, api: TandemnAPI):
        self.api = api
    
    def set_callback(self, callback):
        """Set a callback function for progress updates."""
        self.callback = callback

    def _save_state(self):
        """Save current tasks to a temp file for progress tracking."""
        state = {
            "active": [t.to_dict() for t in self.active_tasks],
            "queue": [t.to_dict() for t in self.queue],
            "history_tail": [t.to_dict() for t in self.history[-10:]] # Keep last 10
        }
        try:
            with open(self.STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save upload state: {e}")

    def _load_state(self):
        """Load state (placeholder for future resume logic)."""
        # For now, we just log that we checked
        if self.STATE_FILE.exists():
            print(f"DEBUG: Found existing state file at {self.STATE_FILE}")

    async def add_files(self, files: List[Path], user_id: str, remote_prefix: str = ""):
        print(f"DEBUG: Adding {len(files)} files to upload queue for user {user_id}")
        for f in files:
            # Simple remote path: just the filename for now
            remote_path = f.name
            if remote_prefix:
                remote_path = f"{remote_prefix}/{f.name}"
                
            task = UploadTask(f, user_id, remote_path)
            self.queue.append(task)
            
        self._save_state()
        if not self.running:
            asyncio.create_task(self.process_queue())

    async def process_queue(self):
        if self.running:
            return
            
        self.running = True
        logging.info(f"DEBUG: Upload Manager started processing queue")
        
        while self.queue:
            task = self.queue.pop(0)
            self.active_tasks.append(task)
            self._save_state()
            
            try:
                await self.upload_file(task)
                self.history.append(task)
            except Exception as e:
                task.status = "error"
                task.error = str(e)
                print(f"Error uploading {task.file_path}: {e}")
                self.history.append(task)
                
                # Notify UI about error
                if self.callback:
                    remaining = len(self.queue) + len(self.active_tasks) - 1
                    await self.callback(f"❌ Failed: {task.file_path.name}", remaining)
            finally:
                if task in self.active_tasks:
                    self.active_tasks.remove(task)
                self._save_state()
                
        self.running = False
        logging.info("DEBUG: Upload Manager finished processing queue")

    async def upload_file(self, task: UploadTask):
        logging.info(f"DEBUG: Starting upload for {task.file_path} ({task.size} bytes)")
        task.status = "uploading"
        
        if task.size < MULTIPART_THRESHOLD:
            await self._upload_single(task)
        else:
            await self._upload_multipart(task)
            
        task.status = "completed"
        task.progress = 100.0
        
        # Notify UI about completion
        if self.callback:
            remaining = len(self.queue) + len(self.active_tasks) - 1  # -1 for current task
            await self.callback(f"✅ Uploaded: {task.file_path.name}", remaining)

    async def _upload_single(self, task: UploadTask):
        # Get presigned URL
        print(f"DEBUG: Requesting presigned URL for {task.remote_path}")
        presigned = await self.api.presign_upload(task.remote_path, task.user_id)
        print(f"DEBUG: Presigned response: {presigned}")  # <-- ADD THIS
        url = presigned["url"]
        headers = presigned.get("headers", {})

        # Upload
        # Use asyncio.to_thread for reading to avoid blocking
        async with httpx.AsyncClient(timeout=None) as client:
            def read_file():
                with open(task.file_path, "rb") as f:
                    return f.read()
            
            content = await asyncio.to_thread(read_file)
            print(f"DEBUG: Uploading {len(content)} bytes with headers: {headers}")
            response = await client.put(url, content=content, headers=headers)
            response.raise_for_status()

    async def _upload_multipart(self, task: UploadTask):
        print(f"DEBUG: Starting multipart upload for {task.remote_path}")
        # Start
        start_res = await self.api.multipart_start(task.remote_path, task.user_id)
        upload_id = start_res["upload_id"]
        task.upload_id = upload_id
        
        part_number = 1
        parts = []
        
        file_obj = await asyncio.to_thread(open, task.file_path, "rb")
        try:
            while True:
                chunk = await asyncio.to_thread(file_obj.read, CHUNK_SIZE)
                if not chunk:
                    break
                
                print(f"DEBUG: Uploading part {part_number} for {task.remote_path}")
                
                # Get sign part
                sign_res = await self.api.multipart_sign_part(upload_id, task.user_id, task.remote_path, part_number)
                url = sign_res["url"]
                headers = sign_res.get("headers", {})
                
                # Upload part
                async with httpx.AsyncClient(timeout=None) as client:
                    res = await client.put(url, content=chunk, headers=headers)
                    res.raise_for_status()
                    
                    # Extract ETag - crucial for S3 multipart complete
                    etag = res.headers.get("ETag")
                    # S3 requires ETag (sometimes with quotes) and PartNumber
                    parts.append({"ETag": etag, "PartNumber": part_number})
                
                # Update progress
                task.uploaded_bytes += len(chunk)
                task.progress = (task.uploaded_bytes / task.size) * 100
                part_number += 1
                
        finally:
            await asyncio.to_thread(file_obj.close)
                
        # Complete
        print(f"DEBUG: Completing multipart upload for {task.remote_path}")
        await self.api.multipart_complete(task.user_id, task.remote_path, upload_id, parts)

