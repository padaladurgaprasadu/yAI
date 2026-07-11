import subprocess
import socket
import os
import requests
from typing import Dict, Any, List

class ToolRegistry:
    """
    Centralized Swarm Tool Registry (Phase 9 Enterprise Feature).
    Encapsulates core execution, system checks, database queries, and git functions
    into standardized agent-invokable APIs.
    """

    @staticmethod
    def execute_terminal_command(command: str, cwd: str = None, timeout: int = 60) -> Dict[str, Any]:
        """Runs arbitrary shell commands safely inside a sub-process."""
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "status": "success" if res.returncode == 0 else "failed",
                "returncode": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds."
            }
        except Exception as e:
            return {
                "status": "error",
                "stdout": "",
                "stderr": str(e)
            }

    @staticmethod
    def git_commit_and_push(repo_dir: str, message: str) -> Dict[str, Any]:
        """Executes full repository staging and commits."""
        ToolRegistry.execute_terminal_command("git add .", cwd=repo_dir)
        commit_res = ToolRegistry.execute_terminal_command(f'git commit -m "{message}"', cwd=repo_dir)
        push_res = ToolRegistry.execute_terminal_command("git push origin main", cwd=repo_dir)
        return {
            "commit": commit_res,
            "push": push_res
        }

    @staticmethod
    def verify_port_active(port: int, host: str = "localhost") -> bool:
        """Verifies if a specific network port is listening/active."""
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False

    @staticmethod
    def check_docker_status() -> bool:
        """Verifies if the Docker engine is running on the host system."""
        res = ToolRegistry.execute_terminal_command("docker info")
        return res["status"] == "success"

    @staticmethod
    def get_http_request(url: str, headers: Dict[str, str] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes a standard REST API GET request."""
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            return {
                "status_code": r.status_code,
                "data": r.json() if "application/json" in r.headers.get("Content-Type", "") else r.text
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": str(e)
            }
