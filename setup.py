"""
兼容旧版 pip 的 setup.py
"""

from setuptools import setup, find_packages

setup(
    name="delta-skillpack",
    version="2.0.0",
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
            "skill=skillpack.cli:main",
        ],
    },
    python_requires=">=3.9",
)
