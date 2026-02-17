"""Comprehensive tests for the validators module.

This module tests all validation functions in validators.py to ensure
data integrity and proper input validation throughout the application.
"""

import pytest
import logging
from unittest.mock import patch

from validators import validate_model_format, validate_partition_size


class TestValidateModelFormat:
    """Test cases for validate_model_format function."""

    def test_accepts_valid_openai_model(self):
        """Test that valid OpenAI model format is accepted."""
        assert validate_model_format("openai:gpt-4") is True

    def test_accepts_valid_model_with_version(self):
        """Test that model format with version numbers is accepted."""
        assert validate_model_format("openai:gpt-5.2") is True
        assert validate_model_format("openai:gpt-3.5-turbo") is True

    def test_accepts_valid_anthropic_model(self):
        """Test that valid Anthropic model format is accepted."""
        assert validate_model_format("anthropic:claude-3") is True
        assert validate_model_format("anthropic:claude-3.5") is True

    def test_accepts_custom_model_names(self):
        """Test that custom model names with various characters are accepted."""
        assert validate_model_format("custom:model-name") is True
        assert validate_model_format("custom:model_v2") is True
        assert validate_model_format("custom:model.name") is True
        assert validate_model_format("my-provider:my-model-1.0") is True

    def test_accepts_model_with_numbers(self):
        """Test that model names containing numbers are accepted."""
        assert validate_model_format("provider1:model2") is True
        assert validate_model_format("provider123:model456") is True

    def test_rejects_model_without_colon(self):
        """Test that model format without colon is rejected."""
        assert validate_model_format("invalid") is False
        assert validate_model_format("openai") is False
        assert validate_model_format("gpt-4") is False

    def test_rejects_empty_string(self):
        """Test that empty string is rejected."""
        assert validate_model_format("") is False

    def test_rejects_none(self):
        """Test that None value is rejected."""
        assert validate_model_format(None) is False

    def test_rejects_only_provider(self):
        """Test that format with only provider and colon is rejected."""
        assert validate_model_format("openai:") is False
        assert validate_model_format("provider:") is False

    def test_rejects_only_model(self):
        """Test that format with only colon and model is rejected."""
        assert validate_model_format(":gpt-4") is False
        assert validate_model_format(":model") is False

    def test_rejects_whitespace_only(self):
        """Test that whitespace-only strings are rejected."""
        assert validate_model_format("   ") is False
        assert validate_model_format("\t") is False
        assert validate_model_format("\n") is False

    def test_rejects_special_characters_in_provider(self):
        """Test that special characters in provider name are rejected."""
        assert validate_model_format("openai!:gpt-4") is False
        assert validate_model_format("openai@:gpt-4") is False
        assert validate_model_format("openai#:gpt-4") is False
        assert validate_model_format("openai$:gpt-4") is False

    def test_rejects_special_characters_in_model(self):
        """Test that special characters in model name are rejected."""
        assert validate_model_format("openai:gpt!4") is False
        assert validate_model_format("openai:gpt@4") is False
        assert validate_model_format("openai:gpt#4") is False
        assert validate_model_format("openai:gpt$4") is False

    def test_rejects_multiple_colons(self):
        """Test that model format with multiple colons is rejected."""
        assert validate_model_format("openai:gpt:4") is False
        assert validate_model_format("a:b:c") is False

    def test_rejects_non_string_types(self):
        """Test that non-string types are rejected."""
        assert validate_model_format(123) is False
        assert validate_model_format(1.5) is False
        assert validate_model_format([]) is False
        assert validate_model_format({}) is False
        assert validate_model_format(True) is False

    def test_logs_debug_on_valid_format(self, caplog):
        """Test that valid format logs debug message."""
        with caplog.at_level(logging.DEBUG):
            validate_model_format("openai:gpt-4")
        assert "Model format validated successfully" in caplog.text
        assert "openai:gpt-4" in caplog.text

    def test_logs_warning_on_invalid_format(self, caplog):
        """Test that invalid format logs warning message."""
        with caplog.at_level(logging.WARNING):
            validate_model_format("invalid")
        assert "Invalid LLM model format" in caplog.text

    def test_logs_debug_on_invalid_type(self, caplog):
        """Test that invalid type logs debug message."""
        with caplog.at_level(logging.DEBUG):
            validate_model_format(123)
        assert "Model validation failed" in caplog.text


class TestValidatePartitionSize:
    """Test cases for validate_partition_size function."""

    def test_accepts_minimum_value(self):
        """Test that minimum valid value (1000) is accepted."""
        assert validate_partition_size(1000) is True

    def test_accepts_maximum_value(self):
        """Test that maximum valid value (10000000) is accepted."""
        assert validate_partition_size(10000000) is True

    def test_accepts_values_within_range(self):
        """Test that values within valid range are accepted."""
        assert validate_partition_size(5000) is True
        assert validate_partition_size(500000) is True
        assert validate_partition_size(5000000) is True

    def test_accepts_float_values(self):
        """Test that float values within range are accepted."""
        assert validate_partition_size(1000.0) is True
        assert validate_partition_size(500000.5) is True
        assert validate_partition_size(10000000.0) is True

    def test_rejects_below_minimum(self):
        """Test that values below minimum (1000) are rejected."""
        assert validate_partition_size(999) is False
        assert validate_partition_size(1) is False
        assert validate_partition_size(0) is False
        assert validate_partition_size(-1) is False

    def test_rejects_above_maximum(self):
        """Test that values above maximum (10000000) are rejected."""
        assert validate_partition_size(10000001) is False
        assert validate_partition_size(100000000) is False
        assert validate_partition_size(999999999) is False

    def test_rejects_negative_values(self):
        """Test that negative values are rejected."""
        assert validate_partition_size(-100) is False
        assert validate_partition_size(-1000) is False
        assert validate_partition_size(-10000000) is False

    def test_rejects_non_numeric_types(self):
        """Test that non-numeric types are rejected."""
        assert validate_partition_size("1000") is False
        assert validate_partition_size("500000") is False
        assert validate_partition_size([]) is False
        assert validate_partition_size({}) is False
        assert validate_partition_size(None) is False

    def test_rejects_boolean_values(self):
        """Test that boolean values are rejected (not numeric)."""
        assert validate_partition_size(True) is False
        assert validate_partition_size(False) is False

    def test_boundary_values(self):
        """Test boundary values around limits."""
        # Just below minimum
        assert validate_partition_size(999) is False
        # At minimum
        assert validate_partition_size(1000) is True
        # Just above minimum
        assert validate_partition_size(1001) is True
        # Just below maximum
        assert validate_partition_size(9999999) is True
        # At maximum
        assert validate_partition_size(10000000) is True
        # Just above maximum
        assert validate_partition_size(10000001) is False

    def test_logs_debug_on_valid_size(self, caplog):
        """Test that valid size logs debug message."""
        with caplog.at_level(logging.DEBUG):
            validate_partition_size(500000)
        assert "Partition size validated successfully" in caplog.text
        assert "500000" in caplog.text

    def test_logs_warning_on_out_of_range(self, caplog):
        """Test that out of range size logs warning message."""
        with caplog.at_level(logging.WARNING):
            validate_partition_size(500)
        assert "Invalid partition size" in caplog.text
        assert "Must be between 1000 and 10000000" in caplog.text

    def test_logs_debug_on_invalid_type(self, caplog):
        """Test that invalid type logs debug message."""
        with caplog.at_level(logging.DEBUG):
            validate_partition_size("invalid")
        assert "Partition size validation failed" in caplog.text
        assert "invalid type" in caplog.text


class TestValidatorIntegration:
    """Integration tests for validators module."""

    def test_validators_work_independently(self):
        """Test that both validators can be used independently."""
        # Validate model
        assert validate_model_format("openai:gpt-4") is True
        assert validate_model_format("invalid") is False

        # Validate partition size
        assert validate_partition_size(500000) is True
        assert validate_partition_size(500) is False

    def test_validators_can_be_used_together(self):
        """Test that validators can be used together in validation logic."""
        settings = {
            "model": "openai:gpt-4",
            "partition_size": 500000
        }

        is_valid = (
            validate_model_format(settings["model"]) and
            validate_partition_size(settings["partition_size"])
        )

        assert is_valid is True

    def test_validation_fails_if_any_validator_fails(self):
        """Test that combined validation fails if any validator fails."""
        # Valid model, invalid size
        assert validate_model_format("openai:gpt-4") is True
        assert validate_partition_size(500) is False

        # Invalid model, valid size
        assert validate_model_format("invalid") is False
        assert validate_partition_size(500000) is True

        # Both invalid
        assert validate_model_format("") is False
        assert validate_partition_size(-1) is False

    def test_real_world_model_formats(self):
        """Test real-world model format examples."""
        real_world_models = [
            "openai:gpt-4",
            "openai:gpt-4-turbo",
            "openai:gpt-3.5-turbo",
            "anthropic:claude-3-opus",
            "anthropic:claude-3-sonnet",
            "anthropic:claude-3-haiku",
            "google:gemini-pro",
            "cohere:command",
            "mistral:mistral-medium",
            "local:llama-2-70b",
        ]

        for model in real_world_models:
            assert validate_model_format(model) is True, f"Failed for {model}"

    def test_real_world_partition_sizes(self):
        """Test real-world partition size examples."""
        real_world_sizes = [
            1000,      # Minimum - small dataset
            10000,     # Small chunk
            100000,    # Medium chunk
            500000,    # Default size
            1000000,   # Large chunk
            5000000,   # Very large chunk
            10000000,  # Maximum - huge dataset
        ]

        for size in real_world_sizes:
            assert validate_partition_size(size) is True, f"Failed for {size}"
