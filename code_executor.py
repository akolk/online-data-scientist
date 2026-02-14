"""Secure code execution module for AI-generated Python code.

This module provides a sandboxed environment for executing untrusted code
with restricted access to Python's built-in functions and modules.
"""

import ast
import logging
from typing import Set, Optional, Dict, Any

logger = logging.getLogger(__name__)

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
    px=None, go=None, folium=None
) -> tuple[bool, Optional[str], Optional[Any]]:
    """
    Securely execute AI-generated Python code.
    
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
    
    try:
        logger.debug(f"Executing validated code:\n{code}")
        exec(code, restricted_globals, global_variables)
        
        # Get the result if present
        result = global_variables.get('result')
        return True, None, result
        
    except Exception as e:
        error_msg = f"Error executing code: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None


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
