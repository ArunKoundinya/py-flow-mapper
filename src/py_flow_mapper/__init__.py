"""
PyFlowMapper - A Python project analyzer and visualization tool.
"""

__version__ = "0.1.0b4.dev"
__author__ = "Arun Koundinya Parasa"
__description__ = "Analyze Python projects and generate dependency graphs"
__github__ = "https://github.com/ArunKoundinya/py-flow-mapper"
__gitpages__ = "https://arunkoundinya.github.io/py-flow-mapper/"

from .analyzer import ProjectAnalyzer
from .mermaid_generator import MermaidGenerator
from .cli import main

__all__ = [
    'ProjectAnalyzer',
    'MermaidGenerator',
    'main'
]