#!/usr/bin/env python3
"""
Setup script for VM Agent package
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_file(filename):
    """Read file contents"""
    try:
        with open(os.path.join(os.path.dirname(__file__), filename), 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        return []

setup(
    name="ai-infra-vm-agent",
    version="1.0.0",
    author="AI Infra Team",
    author_email="contact@ai-infra.com",
    description="Production-ready VM agent for AI infrastructure management with MCP protocol support",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/ai-infra/vm-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Monitoring",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "aiohttp-cors>=0.7.0",
        "pyyaml>=6.0",
        "cryptography>=3.4.8",
        "psutil>=5.8.0",
        "websockets>=10.0",
        "asyncio-mqtt>=0.11.0",
        "pyjwt>=2.4.0",
        "paramiko>=2.11.0",
        "mcp>=1.0.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0",
        ],
        "monitoring": [
            "prometheus-client>=0.14.0",
            "grafana-api>=1.0.3",
        ]
    },
    entry_points={
        "console_scripts": [
            "vm-agent=vm_agent.cli:main",
            "vm-agent-server=vm_agent.server:main",
            "vm-agent-install=vm_agent.installer:main",
        ],
    },
    include_package_data=True,
    package_data={
        "vm_agent": [
            "config/*.yaml",
            "systemd/*.service",
            "scripts/*.sh",
            "templates/*.j2",
        ],
    },
    zip_safe=False,
    keywords="vm agent infrastructure management mcp protocol automation",
    project_urls={
        "Bug Reports": "https://github.com/ai-infra/vm-agent/issues",
        "Source": "https://github.com/ai-infra/vm-agent",
        "Documentation": "https://docs.ai-infra.com/vm-agent",
    },
) 