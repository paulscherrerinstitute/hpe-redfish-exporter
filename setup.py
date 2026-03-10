"""
Setup script for HPE Redfish Exporter package
"""

from setuptools import setup, find_packages
import os

# Read requirements
with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

# Read long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="hpe-redfish-exporter",
    version="2.4.0",
    description="Prometheus exporter for HPE ClusterStor systems using Redfish API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="HPE ClusterStor Exporter Team",
    author_email="",
    license="GPL-3.0-or-later",
    license_files=("LICENSE",),
    url="https://github.com/paulscherrerinstitute/hpe-redfish-exporter",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "hpe-redfish-exporter = hpe_redfish_exporter.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Networking :: Monitoring",
    ],
    keywords=[
        "prometheus",
        "exporter",
        "redfish",
        "hpe",
        "clustorstor",
        "lustre",
        "monitoring",
    ],
    project_urls={
        "Source": "https://github.com/paulscherrerinstitute/hpe-redfish-exporter",
        "Tracker": "https://github.com/paulscherrerinstitute/hpe-redfish-exporter/issues",
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json"],
    },
    zip_safe=False,
)
