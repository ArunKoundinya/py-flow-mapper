"""
PyFlowMapper - A Python project analyzer and visualization tool.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__description__ = "Analyze Python projects and generate dependency graphs"

from .analyzer import ProjectAnalyzer
from .mermaid_generator import MermaidGenerator
from .cli import main

__all__ = [
    'ProjectAnalyzer',
    'MermaidGenerator',
    'main'
]