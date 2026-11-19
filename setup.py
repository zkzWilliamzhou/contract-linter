#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='contract-linter',
    version='1.0.0',
    description='C++26 Contracts Static Analysis Tool',
    author='contract-linter team',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'contract-linter=contract_linter:main',
        ],
    },
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)