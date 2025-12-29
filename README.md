# PyFlowMapper
[![Publish Python Package](https://github.com/ArunKoundinya/py-flow-mapper/actions/workflows/publish.yml/badge.svg)](https://github.com/ArunKoundinya/py-flow-mapper/actions/workflows/publish.yml)


**PyFlowMapper** is a lightweight Python static-analysis tool that helps you understand **how functions connect and how data flows** across your codebase — without running your code.

It is designed for developers who want fast architectural insight into new or existing Python projects.

## What It Does

- Reads Python source files using AST (no execution)
- Detects which functions call which others
- Tracks return-value–based data flow between functions
- Generates clear Mermaid diagrams
- Works with **Python 3.12+**
- Automatically ignores virtual environments

## Quick Install

```bash
# Clone and install
git clone https://github.com/ArunKoundinya/py-flow-mapper.git
cd py-flow-mapper
pip install -e .

# Or install directly
pip install py-flow-mapper
```

## How to Use

### Analyze Your Project

```bash
pyflow analyze /path/to/your/project
```
This creates a `project_meta.json` file with all the analysis results.

### Create Diagrams

```bash
pyflow diagram /path/to/your/project/project_meta.json
```
### See Project Structure

```bash
pyflow structure /path/to/your/project
```
Shows a clean tree view of your project folders and files.

## What You Get

Metadata File — `project_meta.json`

Contains:

- List of all functions and where they are
- Which functions call which others
- How data moves between functions
- All imports and dependencies

One Types of Diagram
- Detailed Flow Graph - Shows modules and data flow

## Requirements
- Python 3.12 or higher

## Common Commands

| Command | What it does |
|---------|--------------|
| `pyflow analyze /path/to/project` | Analyze a project |
| `pyflow diagram /path/to/project/project_meta.json` | Make diagrams |
| `pyflow structure /path/to/project` | Show folder structure |
| `pyflow --help` | Get help |
| `pyflow version` | Check version |

## Features

✅ Works with any Python 3.12+ project  
✅ No need to run your code  
✅ Creates visual diagrams  
✅ Shows data flow between functions  
✅ Handles imports correctly  
✅ Excludes virtual environments automatically  

## Tips

- Start with a small project to see how it works  
- Use `--entry-point` if your main file isn't `main.py`  
- View diagrams in VS Code or GitHub for best results  
- The tool ignores `venv/`, `.venv/`, and other common exclude folders  

## Full Documentation

Full documentation (including examples and architecture diagrams) is available in the `docs/` folder and built using Quarto.

## ⚠ Limitations

PyFlowMapper uses static analysis. It may not fully resolve:

- Runtime imports
- Heavy metaprogramming
- Highly dynamic call patterns

Despite this, it provides a strong and reliable architectural baseline for most Python projects.