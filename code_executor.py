"""Secure code execution module for AI-generated Python code.

This module provides a sandboxed environment for executing untrusted code
with restricted access to Python's built-in functions and modules.
"""

import ast
import logging
import signal
import multiprocessing
import sys
from typing import Set, Optional, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Default timeout for code execution (in seconds)
DEFAULT_EXECUTION_TIMEOUT = 30

# Default resource limits
DEFAULT_MEMORY_LIMIT_MB = 512  # 512 MB default memory limit
DEFAULT_CPU_TIME_LIMIT_SECONDS = 60  # 60 seconds of CPU time

# Check if resource module is available (Unix-like systems)
RESOURCE_AVAILABLE = False
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    pass  # Windows doesn't have resource module


class TimeoutException(Exception):
    """Exception raised when code execution times out."""
    pass


class ResourceLimitException(Exception):
    """Exception raised when code execution exceeds resource limits."""
    pass


def set_resource_limits(
    max_memory_mb: int = DEFAULT_MEMORY_LIMIT_MB,
    max_cpu_time_seconds: int = DEFAULT_CPU_TIME_LIMIT_SECONDS
) -> Tuple[bool, Optional[str]]:
    """
    Set resource limits for the current process.

    Uses the resource module on Unix-like systems to limit memory and CPU usage.
    On Windows, this function returns False as resource limits are not available.

    Args:
        max_memory_mb: Maximum memory allowed in megabytes
        max_cpu_time_seconds: Maximum CPU time allowed in seconds

    Returns:
        Tuple of (success, error_message)
    """
    if not RESOURCE_AVAILABLE:
        return False, "Resource limits not available on this platform"

    try:
        # Set memory limit (soft limit)
        max_memory_bytes = max_memory_mb * 1024 * 1024
        # resource module is guaranteed to be available here because RESOURCE_AVAILABLE is True
        resource_mod = sys.modules.get('resource', None)
        if resource_mod:
            resource_mod.setrlimit(resource_mod.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))

            # Set CPU time limit
            resource_mod.setrlimit(
                resource_mod.RLIMIT_CPU,
                (max_cpu_time_seconds, max_cpu_time_seconds + 5)
            )

        logger.debug(f"Resource limits set: {max_memory_mb}MB memory, {max_cpu_time_seconds}s CPU")
        return True, None

    except (ValueError, OSError) as e:
        return False, f"Failed to set resource limits: {e}"


def get_resource_usage() -> Dict[str, float]:
    """
    Get current resource usage statistics.

    Returns:
        Dictionary with 'memory_mb' and 'cpu_time_seconds' keys
    """
    usage = {
        'memory_mb': 0.0,
        'cpu_time_seconds': 0.0
    }

    try:
        # Get memory usage
        if RESOURCE_AVAILABLE:
            # resource module is guaranteed to be available here because RESOURCE_AVAILABLE is True
            resource_mod = sys.modules.get('resource', None)
            if resource_mod:
                # Get max resident set size in bytes, convert to MB
                rusage = resource_mod.getrusage(resource_mod.RUSAGE_SELF)
                usage['memory_mb'] = rusage.ru_maxrss / 1024  # KB to MB on Linux
                if sys.platform == 'darwin':  # macOS uses bytes instead of KB
                    usage['memory_mb'] = rusage.ru_maxrss / (1024 * 1024)
                usage['cpu_time_seconds'] = rusage.ru_utime + rusage.ru_stime
        else:
            # Fallback: try to get memory from /proc on Linux
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            # Parse "VmRSS:   12345 kB"
                            parts = line.split()
                            if len(parts) >= 2:
                                usage['memory_mb'] = float(parts[1]) / 1024  # KB to MB
                            break
            except (IOError, OSError):
                pass

    except Exception as e:
        logger.debug(f"Could not get resource usage: {e}")

    return usage


@contextmanager
def execution_timeout(seconds: int):
    """
    Context manager that raises TimeoutException after specified seconds.

    Uses signal module on Unix-like systems. On Windows or if signals are
    unavailable, executes code in a separate process for true timeout protection.

    Args:
        seconds: Timeout duration in seconds

    Raises:
        TimeoutException: If execution exceeds the specified time
    """
    def timeout_handler(signum, frame):
        raise TimeoutException(f"Code execution timed out after {seconds} seconds")

    # Try to use signal-based timeout (Unix-like systems)
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        old_alarm = signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)  # Cancel the alarm
            signal.signal(signal.SIGALRM, old_handler)
            if old_alarm > 0:
                signal.alarm(old_alarm)
    else:
        # On Windows or systems without SIGALRM, we can't use signals
        # The actual timeout will be handled by process-based execution
        yield


def _execute_in_process(
    code: str,
    global_vars: Dict[str, Any],
    restricted_globals: Dict[str, Any],
    timeout: int,
    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
    cpu_time_limit_seconds: int = DEFAULT_CPU_TIME_LIMIT_SECONDS
) -> tuple[bool, Optional[str], Optional[Any]]:
    """
    Execute code in a separate process with timeout and resource limits.

    This function is used on Windows or as a fallback when signal-based
    timeout is not available.

    Args:
        code: Python code to execute
        global_vars: Dictionary to store execution results
        restricted_globals: Restricted globals dict
        timeout: Timeout in seconds
        memory_limit_mb: Maximum memory usage in MB (not enforced on Windows)
        cpu_time_limit_seconds: Maximum CPU time in seconds (not enforced on Windows)

    Returns:
        Tuple of (success, error_message, result)
    """
    def target_func(return_dict, code, restricted_globals, memory_limit_mb, cpu_time_limit_seconds):
        # Set resource limits in the child process (Unix only)
        if RESOURCE_AVAILABLE:
            set_resource_limits(memory_limit_mb, cpu_time_limit_seconds)

        try:
            local_vars = {}
            exec(code, restricted_globals, local_vars)
            return_dict['success'] = True
            return_dict['result'] = local_vars.get('result')
            return_dict['globals'] = {k: v for k, v in local_vars.items()
                                      if k != '__builtins__'}
        except MemoryError as e:
            return_dict['success'] = False
            return_dict['error'] = f"MemoryError: Code exceeded memory limit of {memory_limit_mb} MB"
        except Exception as e:
            return_dict['success'] = False
            return_dict['error'] = f"{type(e).__name__}: {str(e)}"

    manager = multiprocessing.Manager()
    return_dict = manager.dict()

    process = multiprocessing.Process(
        target=target_func,
        args=(return_dict, code, restricted_globals, memory_limit_mb, cpu_time_limit_seconds)
    )

    process.start()
    process.join(timeout=timeout)

    if process.is_alive():
        process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()
        return False, f"Code execution timed out after {timeout} seconds", None

    if process.exitcode != 0:
        return False, f"Code execution failed with exit code {process.exitcode}", None

    if 'success' not in return_dict:
        return False, "Code execution failed unexpectedly", None

    if return_dict['success']:
        # Copy results back to global_vars
        if 'globals' in return_dict:
            global_vars.update(return_dict['globals'])
        return True, None, return_dict.get('result')
    else:
        return False, return_dict.get('error', "Unknown error"), None


# Dangerous operations that should be blocked
DANGEROUS_IMPORTS = {
    'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
    'ftplib', 'smtplib', 'telnetlib', 'pickle', 'marshal', 'eval',
    'exec', 'compile', '__import__', 'open', 'input', 'raw_input',
    'reload', 'exit', 'quit'
}

# Dangerous AST node types
DANGEROUS_NODE_TYPES = {
    'Import', 'ImportFrom', 'Call', 'Lambda', 'FunctionDef',
    'ClassDef', 'AsyncFunctionDef', 'Delete'
}

# Allowed built-ins for code execution
SAFE_BUILTINS = {
    'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes',
    'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter',
    'float', 'format', 'frozenset', 'hasattr', 'hash', 'hex',
    'id', 'int', 'isinstance', 'issubclass', 'iter', 'len',
    'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow',
    'range', 'repr', 'reversed', 'round', 'set', 'slice',
    'sorted', 'str', 'sum', 'tuple', 'type', 'vars', 'zip',
    'print'  # Allow print but it's redirected to logger
}


def validate_code(code: str) -> tuple[bool, Optional[str]]:
    """
    Validate AI-generated code for dangerous operations.

    Args:
        code: Python code string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if code is safe to execute
        - error_message: Description of why code is unsafe (None if valid)
    """
    if not code or not code.strip():
        return True, None

    try:
        # Parse the code into an AST
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in generated code: {e}"

    # Walk through all nodes in the AST
    for node in ast.walk(tree):
        # Check for dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name in DANGEROUS_IMPORTS:
                    return False, f"Import of '{module_name}' is not allowed for security reasons"

        # Check for from X import Y statements
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name in DANGEROUS_IMPORTS:
                    return False, f"Import from '{module_name}' is not allowed for security reasons"

        # Check for function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                # Check for eval/exec/compile/__import__/open
                if node.func.id in ('eval', 'exec', 'compile', '__import__', 'open'):
                    return False, f"Call to '{node.func.id}' is not allowed for security reasons"
            elif isinstance(node.func, ast.Attribute):
                # Check for eval/exec on objects
                if node.func.attr in ('eval', 'exec'):
                    return False, f"Call to '{node.func.attr}' is not allowed for security reasons"

    return True, None


def create_restricted_globals(
    pl=None, pd=None, st=None, gpd=None, alt=None,
    px=None, go=None, folium=None
) -> Dict[str, Any]:
    """
    Create a restricted globals dictionary for exec() with only safe built-ins.

    Args:
        pl: polars module (optional)
        pd: pandas module (optional)
        st: streamlit module (optional)
        gpd: geopandas module (optional)
        alt: altair module (optional)
        px: plotly.express module (optional)
        go: plotly.graph_objects module (optional)
        folium: folium module (optional)

    Returns:
        Dictionary suitable for use as globals in exec()
    """
    # Start with restricted built-ins
    restricted_builtins = {name: __builtins__[name] for name in SAFE_BUILTINS if name in __builtins__}

    # Create the globals dict
    restricted_globals = {
        '__builtins__': restricted_builtins,
    }

    # Add allowed modules
    if pl is not None:
        restricted_globals['pl'] = pl
    if pd is not None:
        restricted_globals['pd'] = pd
    if st is not None:
        restricted_globals['st'] = st
    if gpd is not None:
        restricted_globals['gpd'] = gpd
    if alt is not None:
        restricted_globals['alt'] = alt
    if px is not None:
        restricted_globals['px'] = px
    if go is not None:
        restricted_globals['go'] = go
    if folium is not None:
        restricted_globals['folium'] = folium

    return restricted_globals


def execute_code_securely(
    code: str,
    global_variables: Dict[str, Any],
    pl=None, pd=None, st=None, gpd=None, alt=None,
    px=None, go=None, folium=None,
    timeout: int = DEFAULT_EXECUTION_TIMEOUT,
    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
    cpu_time_limit_seconds: int = DEFAULT_CPU_TIME_LIMIT_SECONDS
) -> tuple[bool, Optional[str], Optional[Any]]:
    """
    Securely execute AI-generated Python code with timeout and resource limits.

    Args:
        code: Python code string to execute
        global_variables: Dictionary to store execution results
        pl: polars module (optional)
        pd: pandas module (optional)
        st: streamlit module (optional)
        gpd: geopandas module (optional)
        alt: altair module (optional)
        px: plotly.express module (optional)
        go: plotly.graph_objects module (optional)
        folium: folium module (optional)
        timeout: Maximum execution time in seconds (default: 30)
        memory_limit_mb: Maximum memory usage in MB (default: 512)
        cpu_time_limit_seconds: Maximum CPU time in seconds (default: 60)

    Returns:
        Tuple of (success, error_message, result)
        - success: True if execution succeeded
        - error_message: Error description if failed (None if success)
        - result: Value of 'result' variable if present (None if not)
    """
    # Validate the code first
    is_valid, error_msg = validate_code(code)
    if not is_valid:
        logger.warning(f"Code validation failed: {error_msg}")
        return False, error_msg, None

    # Create restricted globals
    restricted_globals = create_restricted_globals(
        pl=pl, pd=pd, st=st, gpd=gpd, alt=alt,
        px=px, go=go, folium=folium
    )

    logger.debug(f"Executing validated code with {timeout}s timeout:\n{code}")

    # Set resource limits before execution (Unix-like systems)
    set_resource_limits(memory_limit_mb, cpu_time_limit_seconds)

    # Use signal-based timeout on Unix-like systems
    if hasattr(signal, 'SIGALRM'):
        try:
            with execution_timeout(timeout):
                exec(code, restricted_globals, global_variables)

            # Get the result if present
            result = global_variables.get('result')
            return True, None, result

        except TimeoutException as e:
            error_msg = str(e)
            logger.warning(error_msg)
            return False, error_msg, None
        except MemoryError as e:
            error_msg = f"Code exceeded memory limit of {memory_limit_mb} MB"
            logger.warning(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Error executing code: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    else:
        # Use process-based execution on Windows
        return _execute_in_process(code, global_variables, restricted_globals, timeout,
                                   memory_limit_mb, cpu_time_limit_seconds)


def validate_user_input(user_input: str) -> tuple[bool, Optional[str]]:
    """
    Validate user input for potentially malicious content.

    Args:
        user_input: User's chat input

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not user_input or not user_input.strip():
        return False, "Input cannot be empty"

    # Check input length (prevent DoS)
    if len(user_input) > 10000:
        return False, "Input is too long (max 10000 characters)"

    # Check for suspicious patterns
    suspicious_patterns = [
        '__import__',
        'eval(',
        'exec(',
        'compile(',
        'subprocess.',
        'os.system',
        'os.popen',
    ]

    lower_input = user_input.lower()
    for pattern in suspicious_patterns:
        if pattern in lower_input:
            logger.warning(f"Suspicious pattern '{pattern}' detected in user input")
            return False, f"Input contains potentially dangerous pattern: '{pattern}'"

    return True, None
