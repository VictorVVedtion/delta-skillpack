"""
兼容旧版 pip 的 setup.py
"""

from setuptools import setup, find_packages

setup(
    name="delta-skillpack",
    version="5.4.2",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
    ],
    extras_require={
        "rich": ["rich>=13.0.0"],
        "dev": ["pytest>=7.0.0"],
    },
    entry_points={
        "console_scripts": [
            "skillpack=skillpack.cli:cli",
        ],
    },
    python_requires=">=3.9",
)
