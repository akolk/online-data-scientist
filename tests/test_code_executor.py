"""Test suite for code_executor module.

This module tests the secure code execution functionality including:
- Code validation for dangerous operations
- Restricted globals creation
- Secure code execution
- User input validation
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

import code_executor


class TestValidateCode:
    """Test cases for validate_code function."""
    
    def test_valid_simple_code(self):
        """Test that simple, safe code passes validation."""
        code = "result = 1 + 1"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_valid_code_with_variables(self):
        """Test code with variable assignments."""
        code = """
x = 10
y = 20
result = x + y
"""
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_valid_code_with_loops(self):
        """Test code with for loops."""
        code = """
result = 0
for i in range(10):
    result += i
"""
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_blocks_os_import(self):
        """Test that importing os is blocked."""
        code = "import os"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "os" in error_msg.lower()
        assert "not allowed" in error_msg.lower()
    
    def test_blocks_sys_import(self):
        """Test that importing sys is blocked."""
        code = "import sys"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "sys" in error_msg.lower()
    
    def test_blocks_subprocess_import(self):
        """Test that importing subprocess is blocked."""
        code = "import subprocess"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "subprocess" in error_msg.lower()
    
    def test_blocks_eval_call(self):
        """Test that eval() calls are blocked."""
        code = "result = eval('1 + 1')"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "eval" in error_msg.lower()
    
    def test_blocks_exec_call(self):
        """Test that exec() calls are blocked."""
        code = "exec('result = 1 + 1')"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "exec" in error_msg.lower()
    
    def test_blocks_open_call(self):
        """Test that open() calls are blocked."""
        code = "f = open('test.txt', 'r')"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "open" in error_msg.lower()
    
    def test_blocks_from_import(self):
        """Test that 'from os import' is blocked."""
        code = "from os import system"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "os" in error_msg.lower()
    
    def test_blocks_requests_import(self):
        """Test that importing requests is blocked."""
        code = "import requests"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "requests" in error_msg.lower()
    
    def test_detects_syntax_error(self):
        """Test that syntax errors are caught."""
        code = "result = 1 +"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "syntax error" in error_msg.lower()
    
    def test_empty_code_is_valid(self):
        """Test that empty code is considered valid."""
        is_valid, error_msg = code_executor.validate_code("")
        
        assert is_valid is True
        assert error_msg is None
        
        is_valid, error_msg = code_executor.validate_code("   ")
        
        assert is_valid is True
        assert error_msg is None
    
    def test_blocks_socket_import(self):
        """Test that importing socket is blocked."""
        code = "import socket"
        is_valid, error_msg = code_executor.validate_code(code)
        
        assert is_valid is False
        assert "socket" in error_msg.lower()


class TestCreateRestrictedGlobals:
    """Test cases for create_restricted_globals function."""
    
    def test_creates_dict_with_builtins(self):
        """Test that function creates a globals dict with __builtins__."""
        globals_dict = code_executor.create_restricted_globals()
        
        assert '__builtins__' in globals_dict
        assert isinstance(globals_dict['__builtins__'], dict)
    
    def test_restricts_builtins(self):
        """Test that dangerous built-ins are not included."""
        globals_dict = code_executor.create_restricted_globals()
        builtins = globals_dict['__builtins__']
        
        # Should not have dangerous builtins
        assert 'open' not in builtins
        assert 'eval' not in builtins
        assert 'exec' not in builtins
        assert '__import__' not in builtins
    
    def test_includes_safe_builtins(self):
        """Test that safe built-ins are included."""
        globals_dict = code_executor.create_restricted_globals()
        builtins = globals_dict['__builtins__']
        
        # Should have safe builtins
        assert 'len' in builtins
        assert 'range' in builtins
        assert 'str' in builtins
        assert 'int' in builtins
        assert 'sum' in builtins
        assert 'max' in builtins
        assert 'min' in builtins
    
    def test_includes_data_modules(self):
        """Test that data modules are included when provided."""
        mock_pl = Mock()
        mock_pd = Mock()
        
        globals_dict = code_executor.create_restricted_globals(pl=mock_pl, pd=mock_pd)
        
        assert globals_dict['pl'] is mock_pl
        assert globals_dict['pd'] is mock_pd
    
    def test_excludes_none_modules(self):
        """Test that None modules are not included."""
        globals_dict = code_executor.create_restricted_globals(pl=None, pd=Mock())
        
        assert 'pl' not in globals_dict
        assert 'pd' in globals_dict
    
    def test_includes_all_allowed_modules(self):
        """Test that all allowed modules can be included."""
        mocks = {
            'pl': Mock(),
            'pd': Mock(),
            'st': Mock(),
            'gpd': Mock(),
            'alt': Mock(),
            'px': Mock(),
            'go': Mock(),
            'folium': Mock()
        }
        
        globals_dict = code_executor.create_restricted_globals(**mocks)
        
        for key, mock_obj in mocks.items():
            assert globals_dict[key] is mock_obj


class TestExecuteCodeSecurely:
    """Test cases for execute_code_securely function."""
    
    def test_executes_simple_code(self):
        """Test that simple code executes successfully."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="result = 1 + 1",
            global_variables=global_vars
        )
        
        assert success is True
        assert error_msg is None
        assert result == 2
    
    def test_returns_result_variable(self):
        """Test that result variable is returned."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="x = 10\ny = 20\nresult = x + y",
            global_variables=global_vars
        )
        
        assert success is True
        assert result == 30
    
    def test_handles_code_without_result(self):
        """Test that code without result variable returns None."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="x = 10",
            global_variables=global_vars
        )
        
        assert success is True
        assert result is None
    
    def test_blocks_dangerous_code(self):
        """Test that dangerous code is blocked before execution."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="import os",
            global_variables=global_vars
        )
        
        assert success is False
        assert error_msg is not None
        assert "os" in error_msg.lower()
        assert result is None
    
    def test_handles_runtime_error(self):
        """Test that runtime errors are handled gracefully."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="result = 1 / 0",
            global_variables=global_vars
        )
        
        assert success is False
        assert "ZeroDivisionError" in error_msg or "error executing code" in error_msg.lower()
        assert result is None
    
    def test_handles_name_error(self):
        """Test that name errors are handled gracefully."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="result = undefined_variable",
            global_variables=global_vars
        )
        
        assert success is False
        assert "NameError" in error_msg
        assert result is None
    
    def test_makes_modules_available(self):
        """Test that provided modules are available in execution."""
        mock_module = Mock()
        mock_module.value = 42
        
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="result = pl.value",
            global_variables=global_vars,
            pl=mock_module
        )
        
        assert success is True
        assert result == 42


class TestValidateUserInput:
    """Test cases for validate_user_input function."""
    
    def test_valid_simple_input(self):
        """Test that simple text input is valid."""
        is_valid, error_msg = code_executor.validate_user_input("Hello, how are you?")
        
        assert is_valid is True
        assert error_msg is None
    
    def test_rejects_empty_input(self):
        """Test that empty input is rejected."""
        is_valid, error_msg = code_executor.validate_user_input("")
        
        assert is_valid is False
        assert "empty" in error_msg.lower()
    
    def test_rejects_whitespace_input(self):
        """Test that whitespace-only input is rejected."""
        is_valid, error_msg = code_executor.validate_user_input("   \n\t  ")
        
        assert is_valid is False
        assert "empty" in error_msg.lower()
    
    def test_rejects_long_input(self):
        """Test that very long input is rejected."""
        long_input = "a" * 10001
        is_valid, error_msg = code_executor.validate_user_input(long_input)
        
        assert is_valid is False
        assert "too long" in error_msg.lower()
    
    def test_rejects_eval_in_input(self):
        """Test that input containing eval() is rejected."""
        is_valid, error_msg = code_executor.validate_user_input("Can you eval(1+1)?")
        
        assert is_valid is False
        assert "eval" in error_msg.lower()
    
    def test_rejects_exec_in_input(self):
        """Test that input containing exec() is rejected."""
        is_valid, error_msg = code_executor.validate_user_input("Please exec('print(1)')")
        
        assert is_valid is False
        assert "exec" in error_msg.lower()
    
    def test_rejects_subprocess_in_input(self):
        """Test that input containing subprocess is rejected."""
        is_valid, error_msg = code_executor.validate_user_input("Use subprocess.call()")
        
        assert is_valid is False
        assert "subprocess" in error_msg.lower()
    
    def test_rejects_os_system_in_input(self):
        """Test that input containing os.system is rejected."""
        is_valid, error_msg = code_executor.validate_user_input("Run os.system('ls')")
        
        assert is_valid is False
        assert "os.system" in error_msg.lower()
    
    def test_rejects_import_in_input(self):
        """Test that input containing __import__ is rejected."""
        is_valid, error_msg = code_executor.validate_user_input("Call __import__('os')")
        
        assert is_valid is False
        assert "__import__" in error_msg.lower()
    
    def test_allows_normal_data_analysis_query(self):
        """Test that normal data analysis queries are allowed."""
        queries = [
            "Show me the first 10 rows of the dataset",
            "What is the average value of column X?",
            "Create a bar chart of sales by month",
            "Calculate the correlation between columns A and B",
            "Filter rows where value > 100",
        ]
        
        for query in queries:
            is_valid, error_msg = code_executor.validate_user_input(query)
            assert is_valid is True, f"Query should be valid: {query}"
            assert error_msg is None, f"Error should be None for: {query}"


class TestExecutionTimeout:
    """Test cases for code execution timeout functionality."""
    
    def test_executes_code_within_timeout(self):
        """Test that code executing within timeout succeeds."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="result = 1 + 1",
            global_variables=global_vars,
            timeout=5
        )
        
        assert success is True
        assert error_msg is None
        assert result == 2
    
    def test_times_out_infinite_loop(self):
        """Test that infinite loops are terminated by timeout."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="while True: pass",
            global_variables=global_vars,
            timeout=1  # Short timeout for test
        )
        
        assert success is False
        assert "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
        assert result is None
    
    def test_times_out_slow_computation(self):
        """Test that slow computations respect timeout."""
        # This code will take a long time without timeout (CPU-intensive loop)
        # Using a busy-wait loop since time.sleep is not available in restricted environment
        code = """
i = 0
while i < 1000000000:
    i += 1
result = "completed"
"""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code=code,
            global_variables=global_vars,
            timeout=1  # Short timeout for test
        )
        
        assert success is False
        assert "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
    
    def test_default_timeout_applied(self):
        """Test that default timeout is used when not specified."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="result = 42",
            global_variables=global_vars
        )
        
        assert success is True
        assert result == 42
    
    def test_respects_custom_timeout(self):
        """Test that custom timeout parameter is respected."""
        global_vars = {}
        success, error_msg, result = code_executor.execute_code_securely(
            code="result = sum(range(100))",
            global_variables=global_vars,
            timeout=10
        )
        
        assert success is True
        assert result == 4950


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
