"""Setup configuration for ActionsGuard."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version
version = {}
with open("actionsguard/__version__.py") as f:
    exec(f.read(), version)

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="actionsguard",
    version=version["__version__"],
    description="GitHub Actions security scanner using OpenSSF Scorecard",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    author="Travis Felder",
    author_email="travis@cybrking.com",
    url="https://github.com/cybrking/actions-guard",
    project_urls={
        "Bug Tracker": "https://github.com/cybrking/actions-guard/issues",
        "Documentation": "https://github.com/cybrking/actions-guard#readme",
        "Source Code": "https://github.com/cybrking/actions-guard",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "actionsguard": ["templates/*.html"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "PyGithub>=2.1.1",
        "click>=8.1.0",
        "rich>=13.0.0",
        "jinja2>=3.1.0",
        "requests>=2.31.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "types-requests>=2.31.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "actionsguard=actionsguard.cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Security",
        "Topic :: Software Development :: Quality Assurance",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="github actions security scanner ossf scorecard",
)
