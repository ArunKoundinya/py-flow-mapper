from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="py-flow-mapper",
    version="0.1.0b5.dev",
    author="Arun Koundinya Parasa",
    author_email="parasa.arunkoundinya@gmail.com",
    description="Python project analyzer and visualization tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ArunKoundinya/py-flow-mapper",
    project_urls={
        "Documentation": "https://arunkoundinya.github.io/py-flow-mapper/",
        "Source": "https://github.com/ArunKoundinya/py-flow-mapper",
        "Issues": "https://github.com/ArunKoundinya/py-flow-mapper/issues",
        "Changelog": "https://github.com/ArunKoundinya/py-flow-mapper/releases",
    },
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=[
        "astunparse>=1.6.3; python_version < '3.9'",
    ],
    keywords=[
        "static-analysis",
        "call-graph",
        "data-flow",
        "mermaid",
        "python-analysis",
    ],
    entry_points={
        "console_scripts": [
            "pyflow=py_flow_mapper.cli:main",
        ],
    },
)