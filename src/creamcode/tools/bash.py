import asyncio
import subprocess
from typing import Optional

from .decorator import tool


@tool(
    name="Bash",
    description="Execute a shell command in the terminal. Use this for file operations, running scripts, installing packages, etc."
)
async def bash(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    """
    Execute a shell command
    
    Args:
        command: The shell command to execute
        timeout: Timeout in seconds (default: 30)
        cwd: Working directory (optional)
    
    Returns:
        Command output (stdout + stderr)
    """
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            raise
        
        output = ""
        if stdout:
            output += stdout.decode('utf-8', errors='replace')
        if stderr:
            output += "\n[stderr]\n" + stderr.decode('utf-8', errors='replace')
        
        if proc.returncode != 0:
            output += f"\n[exit code: {proc.returncode}]"
        
        return output.strip()
        
    except asyncio.TimeoutError:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error: {str(e)}"