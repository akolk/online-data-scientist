
import io
import pandas as pd
import polars as pl

def test_execution_logic():
    code = """
print("Hello world")
print("Line 2")
output_df = pd.DataFrame({'a': [1, 2]})
"""
    output_buffer = io.StringIO()
    def safe_print(*args, **kwargs):
        print(*args, file=output_buffer, **kwargs)

    local_scope = {}
    globals_scope = {'pl': pl, 'pd': pd, 'print': safe_print}

    exec(code, globals_scope, local_scope)

    output = output_buffer.getvalue()
    print(f"Captured output:\n{output}")

    expected_output = "Hello world\nLine 2\n"
    assert output == expected_output, f"Expected '{expected_output}', got '{output}'"

    assert 'output_df' in local_scope
    df = local_scope['output_df']
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 1)
    print("Test passed!")

if __name__ == "__main__":
    test_execution_logic()
