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

One Type of Diagram
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

## Diagram Options

### Layout Direction

By default, diagrams are generated in both top-down (`TD`) and left-right (`LR`) layouts. You can control this with `--layout`:

```bash
pyflow diagram project_meta.json --layout LR
```

| Layout | Best for |
|--------|----------|
| `TD` (default) | Following execution order top to bottom |
| `LR` | Seeing project vs external library boundary |

### Including External Libraries

By default, external library calls (e.g. `pandas`, `numpy`, `sklearn`) are hidden from diagrams to reduce noise. You can opt in to showing specific libraries using `--include-external`:

```bash
# Show pandas and numpy calls in the diagram
pyflow diagram project_meta.json --include-external pandas,numpy

# Show sklearn pipeline components
pyflow diagram project_meta.json --include-external sklearn

# Combine with layout option
pyflow diagram project_meta.json --include-external pandas,sklearn --layout LR
```

This is especially useful for data-heavy projects where you want to see where data enters (e.g. `pd.read_csv`) or leaves the system (e.g. model exports).

> **Note:** The library names you pass should match the top-level import name used in your code (e.g. `pandas` not `pd`, `sklearn` not `scikit-learn`).

### Showing Data Flow Edges

Data-flow edges (dashed arrows showing return values being passed between functions) are hidden by default. Enable them with `--show-dataflow`:

```bash
pyflow diagram project_meta.json --show-dataflow

# Combine all options
pyflow diagram project_meta.json --include-external pandas,sklearn --show-dataflow --layout LR
```

## Features

✅ Works with any Python 3.12+ project  
✅ No need to run your code  
✅ Creates visual diagrams  
✅ Shows data flow between functions  
✅ Handles imports correctly  
✅ Excludes virtual environments automatically  
✅ Opt-in visibility for external library calls  

## Tips

- Start with a small project to see how it works  
- Use `--entry-point` if your main file isn't `main.py`  
- View diagrams in VS Code or GitHub for best results  
- The tool ignores `venv/`, `.venv/`, and other common exclude folders  
- Use `--include-external` to reveal how your project interacts with third-party libraries  
- Use `--show-dataflow` to trace how return values move between functions  

## Full Documentation

Full documentation (including examples and architecture diagrams) is available in the `docs/` folder and built using Quarto.

## ⚠ Limitations

PyFlowMapper uses static analysis. It may not fully resolve:

- Runtime imports
- Heavy metaprogramming
- Highly dynamic call patterns

Despite this, it provides a strong and reliable architectural baseline for most Python projects.