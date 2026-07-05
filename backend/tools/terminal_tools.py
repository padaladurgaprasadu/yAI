import subprocess
import os
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Basic sandboxed execution environment tools for the Agentic loop

@tool
def execute_bash_command(command: str, cwd: str = ".") -> str:
    """
    Executes a bash command in the specified directory. 
    Use this to run tests (e.g. pytest, npm test), install dependencies, or check syntax (flake8).
    
    Args:
        command: The shell command to run.
        cwd: The working directory for the command.
        
    Returns:
        The standard output and standard error from the command.
    """
    try:
        logger.info(f"Executing command: {command} in {cwd}")
        # Security: In a real production system, this should be inside a secure container (e.g., Docker).
        result = subprocess.run(
            command, 
            cwd=cwd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\nEXIT_CODE: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

@tool
def read_file(filepath: str) -> str:
    """
    Reads the content of a file from the disk.
    
    Args:
        filepath: The absolute or relative path to the file.
        
    Returns:
        The content of the file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {filepath}: {str(e)}"

@tool
def write_file(filepath: str, content: str) -> str:
    """
    Writes content to a file, replacing any existing content.
    Creates directories if they don't exist.
    
    Args:
        filepath: The path to the file to create or overwrite.
        content: The text content to write.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing to file {filepath}: {str(e)}"

# Provide a list of all tools for easy binding
AGENT_TOOLS = [execute_bash_command, read_file, write_file]
