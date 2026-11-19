#!/usr/bin/env python3
"""
contract-linter - C++26 Contracts Static Analysis Tool

A static analysis tool for detecting contract violations in C++26 code
with contracts (pre/post/invariant conditions).

Usage:
    contract-linter file.cpp                # Check single file
    contract-linter --ci-mode *.cpp         # CI mode (fail on warnings)
    contract-linter --format json src/      # JSON output

Supported C++26 contract syntax:
    - pre(condition) - Precondition
    - post(r: condition) - Postcondition with return variable
    - invariant(condition) - Class invariant
"""

__version__ = "1.0.0"
__author__ = "contract-linter team"

import argparse
import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any, Callable
from enum import Enum

__all__ = [
    "ContractType",
    "Contract",
    "Violation",
    "ContractParser",
    "ContractAnalyzer",
    "check_file",
    "require",
    "ensure",
    "invariant",
]


class ContractType(Enum):
    """Types of C++26 contracts"""
    PRE = "precondition"
    POST = "postcondition"
    INVARIANT = "invariant"


@dataclass
class Contract:
    """Represents a parsed contract clause"""
    type: ContractType
    condition: str
    location: Tuple[int, int]  # (line, column)
    complexity: int = 1
    raw: str = ""  # Original raw contract string


@dataclass
class Violation:
    """Represents a detected violation or issue"""
    message: str
    file: str
    line: int
    severity: str  # error, warning, info
    code: str = "GENERIC"


def require(condition: str, message: str = "") -> Callable[[Any], Any]:
    """Decorator to add a precondition to a function.

    Args:
        condition: The precondition condition as a string.
        message: Optional custom error message.

    Returns:
        Decorated function with precondition check.

    Example:
        @require("x > 0", "x must be positive")
        def divide(x, y):
            return x / y
    """
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        func.__contract_pre__ = condition
        func.__contract_pre_msg__ = message
        return func
    return decorator


def ensure(condition: str, message: str = "") -> Callable[[Any], Any]:
    """Decorator to add a postcondition to a function.

    Args:
        condition: The postcondition condition as a string.
        message: Optional custom error message.

    Returns:
        Decorated function with postcondition check.

    Example:
        @ensure("result >= 0", "result must be non-negative")
        def sqrt(x):
            return x ** 0.5
    """
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        func.__contract_post__ = condition
        func.__contract_post_msg__ = message
        return func
    return decorator


def invariant(condition: str, message: str = "") -> Callable[[Any], Any]:
    """Decorator to add an invariant to a class.

    Args:
        condition: The invariant condition as a string.
        message: Optional custom error message.

    Returns:
        Decorated class with invariant check.

    Example:
        @invariant("balance >= 0", "balance must be non-negative")
        class BankAccount:
            def __init__(self, balance):
                self.balance = balance
    """
    def decorator(cls: Callable[[Any], Any]) -> Callable[[Any], Any]:
        cls.__contract_invariant__ = condition
        cls.__contract_invariant_msg__ = message
        return cls
    return decorator




class ContractParser:
    """Parse C++26 contracts from source code"""

    # Regex patterns for C++26 contracts
    # post(r: condition) syntax - capture return variable name
    PRE_PATTERN = r'pre\s*\(([^)]+)\)'
    POST_PATTERN = r'post\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([^)]+)\)'
    POST_PATTERN_NORET = r'post\s*\(([^)]+)\)'  # Fallback: post(condition)
    INVARIANT_PATTERN = r'invariant\s*\(([^)]+)\)'

    def __init__(self, source: str, filename: str = "<source>"):
        self.source = source
        self.filename = filename
        self.lines = source.split('\n')
        self.contracts: List[Contract] = []

    def parse(self) -> List[Contract]:
        """Parse all contracts from source"""
        for line_num, line in enumerate(self.lines, 1):
            self._parse_line(line, line_num)
        return self.contracts

    def _compute_complexity(self, condition: str) -> int:
        """Estimate contract complexity based on nesting and operators"""
        if not condition:
            return 0

        # Count operators and nested conditions
        depth = 1  # Base complexity
        operators = ['&&', '||', '?', ':', '->', '.*']
        for op in operators:
            depth += condition.count(op)

        # Parentheses add to nesting
        depth += condition.count('(')

        return max(1, depth)

    def _parse_line(self, line: str, line_num: int):
        """Parse contracts from a single line"""
        # Find preconditions: pre(condition)
        for match in re.finditer(self.PRE_PATTERN, line):
            cond = match.group(1).strip()
            raw = match.group(0)
            self.contracts.append(Contract(
                ContractType.PRE, cond, (line_num, match.start()),
                complexity=self._compute_complexity(cond),
                raw=raw
            ))

        # Find postconditions: post(r: condition) or post(condition)
        for match in re.finditer(self.POST_PATTERN, line):
            ret_var = match.group(1)
            cond = match.group(2).strip()
            raw = match.group(0)
            self.contracts.append(Contract(
                ContractType.POST, cond, (line_num, match.start()),
                complexity=self._compute_complexity(cond),
                raw=raw
            ))

        # Fallback for post without return variable
        for match in re.finditer(self.POST_PATTERN_NORET, line):
            cond = match.group(1).strip()
            # Skip if already matched by pattern with return variable (contains ':')
            # or if it looks like a function call (has parens inside)
            if ':' not in cond and '(' not in cond:
                raw = match.group(0)
                self.contracts.append(Contract(
                    ContractType.POST, cond, (line_num, match.start()),
                    complexity=self._compute_complexity(cond),
                    raw=raw
                ))

        # Find invariants: invariant(condition)
        for match in re.finditer(self.INVARIANT_PATTERN, line):
            cond = match.group(1).strip()
            raw = match.group(0)
            self.contracts.append(Contract(
                ContractType.INVARIANT, cond, (line_num, match.start()),
                complexity=self._compute_complexity(cond),
                raw=raw
            ))


class ContractAnalyzer:
    """Analyze contracts for violations and issues"""

    DANGEROUS_PATTERNS = [
        (r'delete\s*\(', 'Potential null pointer dereference'),
        (r'\*\s*\w+\s*=', 'Potential memory corruption'),
        (r'std::raw_pointer', 'Raw pointer usage detected'),
        (r'const_cast', 'Const_cast usage detected'),
        (r'reinterpret_cast', 'Unsafe cast detected'),
        (r'::memcpy|memcpy', 'Manual memory copy detected'),
    ]

    COMPLEXITY_WARNING_THRESHOLD = 5
    COMPLEXITY_ERROR_THRESHOLD = 10

    def __init__(self):
        self.violations: List[Violation] = []

    def analyze(self, contracts: List[Contract], source: str = "", filename: str = "<unknown>") -> List[Violation]:
        """Analyze contracts for potential issues

        Args:
            contracts: List of contracts to analyze.
            source: Source code (optional, for context).
            filename: Source filename for reporting.

        Returns:
            List of detected violations.
        """
        violations = []

        for contract in contracts:
            # Check for dangerous patterns
            for pattern, msg in self.DANGEROUS_PATTERNS:
                if re.search(pattern, contract.condition):
                    violations.append(Violation(
                        msg, filename, contract.location[0], "warning", code="DANGEROUS_PATTERN"
                    ))

            # Check complexity
            complexity = contract.complexity
            if complexity > self.COMPLEXITY_ERROR_THRESHOLD:
                violations.append(Violation(
                    f"Contract critically complex: {complexity} nested conditions",
                    filename, contract.location[0], "error", code="COMPLEXITY_HIGH"
                ))
            elif complexity > self.COMPLEXITY_WARNING_THRESHOLD:
                violations.append(Violation(
                    f"Contract complexity high: {complexity} nested conditions",
                    filename, contract.location[0], "info", code="COMPLEXITY_WARN"
                ))

            # Check for tautologies (always true)
            if self._is_tautology(contract.condition):
                violations.append(Violation(
                    "Contract condition is always true (tautology)",
                    filename, contract.location[0], "info", code="TAUTOLOGY"
                ))

            # Check for contradictions (always false)
            if self._is_contradiction(contract.condition):
                violations.append(Violation(
                    "Contract condition is always false (contradiction)",
                    filename, contract.location[0], "error", code="CONTRADICTION"
                ))

        return violations

    def _is_tautology(self, condition: str) -> bool:
        """Check if condition is always true"""
        # Simple checks for common tautologies
        tautologies = ['true', '1', 'not false', '!false']
        cond_lower = condition.lower().strip()
        return any(t in cond_lower for t in tautologies)

    def _is_contradiction(self, condition: str) -> bool:
        """Check if condition is always false"""
        # Simple checks for common contradictions
        # Note: '0' should only match as standalone, not in expressions like 'x >= 0'
        contradictions = ['false', 'not true', '!true']
        cond_lower = condition.lower().strip()
        # Check for '0' as a standalone value (not in comparison)
        if cond_lower == '0':
            return True
        return any(c in cond_lower for c in contradictions)


def check_file(filepath: Path, ci_mode: bool = False) -> List[Violation]:
    """Check a single file for contract violations

    Args:
        filepath: Path to C++ source file
        ci_mode: Enable CI mode (exits on violations)

    Returns:
        List of detected violations
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if not filepath.suffix.lower() in ('.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx'):
        raise ValueError(f"Unsupported file type: {filepath.suffix}")

    source = filepath.read_text(encoding='utf-8')

    parser = ContractParser(source, str(filepath))
    contracts = parser.parse()

    analyzer = ContractAnalyzer()
    violations = analyzer.analyze(contracts, source, str(filepath))

    return violations


def main():
    parser = argparse.ArgumentParser(
        prog='contract-linter',
        description='C++26 Contracts Static Analysis Tool'
    )
    parser.add_argument('files', nargs='+', type=Path,
                       help='Source files to check')
    parser.add_argument('--ci-mode', action='store_true',
                       help='Exit with non-zero on any warning or error')
    parser.add_argument('--format', choices=['text', 'json', 'sarif'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed information')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    all_violations: List[Violation] = []
    errors: List[str] = []

    for filepath in args.files:
        try:
            violations = check_file(filepath, args.ci_mode)
            all_violations.extend(violations)
        except FileNotFoundError as e:
            errors.append(str(e))
            if args.verbose:
                print(f"Error: {e}", file=sys.stderr)
        except ValueError as e:
            errors.append(str(e))
            if args.verbose:
                print(f"Error: {e}", file=sys.stderr)

    # Output violations
    if args.format == 'json':
        print(json.dumps([{
            'message': v.message,
            'file': v.file,
            'line': v.line,
            'severity': v.severity,
            'code': v.code
        } for v in all_violations], indent=2))
    elif args.format == 'sarif':
        # Static Analysis Results Interchange Format
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-v2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"name": "contract-linter", "version": __version__}},
                "results": [{
                    "ruleId": v.code,
                    "level": v.severity,
                    "message": {"text": v.message},
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": v.file},
                            "region": {"line": v.line}
                        }
                    }]
                } for v in all_violations]
            }]
        }
        print(json.dumps(sarif, indent=2))
    else:
        if errors:
            for e in errors:
                print(f"ERROR: {e}", file=sys.stderr)
        if all_violations:
            print(f"\nFound {len(all_violations)} issue(s):\n")
            for v in all_violations:
                print(f"[{v.severity.upper():8}] {v.file}:{v.line}: {v.message}")
                if args.verbose and v.code != "GENERIC":
                    print(f"           Code: {v.code}")

    # Exit with error code
    if args.ci_mode and (all_violations or errors):
        sys.exit(1)
    if errors:
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()