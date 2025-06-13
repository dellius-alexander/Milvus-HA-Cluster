#!/usr/bin/env python3
# File: src.exceptions.py

# Custom exceptions
class MilvusAPIError(Exception):
    """Base exception for Milvus API errors."""

    pass


class MilvusValidationError(MilvusAPIError):
    """Exception raised for validation errors in Milvus API."""

    pass
