#!/usr/bin/env python
"""Simple wrapper to run validation test"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "test_scientific_validation_v3.py"],
    cwd="d:/01_project/王牌项目-从idea到产品/AI科学家（auto_research）",
    capture_output=False
)
sys.exit(result.returncode)
