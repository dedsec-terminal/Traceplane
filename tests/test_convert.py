import pytest
import sys
from unittest.mock import patch
from traceplane.convert import convert

def test_missing_yaml_dependency_exits(capsys):
    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == 'yaml':
            raise ImportError("No module named 'yaml'")
        return original_import(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=mock_import):
        with pytest.raises(SystemExit) as excinfo:
            convert(input_paths=[], output_path='-', yaml_out=True)

        assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "Error: PyYAML is not installed. Please install with: pip install traceplane[yaml]" in captured.err
