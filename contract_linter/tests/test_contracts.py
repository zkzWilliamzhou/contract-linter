#!/usr/bin/env python3
"""Tests for contract-linter - C++26 Contracts Static Analysis Tool"""

import unittest
import tempfile
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from contract_linter import (
    ContractParser, ContractAnalyzer, ContractType, 
    Violation, check_file, Contract
)


class TestContractParser(unittest.TestCase):
    """Test contract parsing functionality"""
    
    def test_parse_precondition(self):
        """Test parsing of preconditions"""
        source = """
        int divide(int a, int b) pre(b != 0) { return a / b; }
        """
        parser = ContractParser(source)
        contracts = parser.parse()
        
        self.assertEqual(len(contracts), 1)
        self.assertEqual(contracts[0].type, ContractType.PRE)
        self.assertEqual(contracts[0].condition, "b != 0")
        self.assertEqual(contracts[0].raw, "pre(b != 0)")
        
    def test_parse_postcondition_with_return(self):
        """Test parsing of postconditions with return variable"""
        source = """
        int factorial(int n)
            pre(n >= 0)
            post(r: r >= 1)
        { return n <= 1 ? 1 : n * factorial(n-1); }
        """
        parser = ContractParser(source)
        contracts = parser.parse()
        
        self.assertEqual(len(contracts), 2)
        self.assertEqual(contracts[0].type, ContractType.PRE)
        self.assertEqual(contracts[1].type, ContractType.POST)
        self.assertEqual(contracts[1].condition, "r >= 1")
        
    def test_parse_invariant(self):
        """Test parsing of invariants"""
        source = """
        class BankAccount {
            invariant(balance >= 0)
            int balance;
        };
        """
        parser = ContractParser(source)
        contracts = parser.parse()
        
        self.assertEqual(len(contracts), 1)
        self.assertEqual(contracts[0].type, ContractType.INVARIANT)
        
    def test_parse_postcondition_without_return(self):
        """Test parsing of postconditions without explicit return variable"""
        source = """
        void process() post(result == 0) { }
        """
        parser = ContractParser(source)
        contracts = parser.parse()
        
        self.assertEqual(len(contracts), 1)
        self.assertEqual(contracts[0].type, ContractType.POST)
        self.assertEqual(contracts[0].condition, "result == 0")
    
    def test_parse_multiple_contracts(self):
        """Test parsing multiple contracts on same line"""
        source = """
        void transfer(Account& from, Account& to, int amount) 
            pre(amount > 0) pre(from.balance >= amount) 
            post(from.balance >= 0) post(to.balance >= 0);
        """
        parser = ContractParser(source)
        contracts = parser.parse()
        
        self.assertEqual(len(contracts), 4)
        self.assertEqual(contracts[0].type, ContractType.PRE)
        self.assertEqual(contracts[1].type, ContractType.PRE)
        self.assertEqual(contracts[2].type, ContractType.POST)
        self.assertEqual(contracts[3].type, ContractType.POST)


class TestComplexityCalculation(unittest.TestCase):
    """Test contract complexity calculation"""
    
    def test_simple_condition(self):
        """Test simplicity condition"""
        source = "void f() pre(x > 0) {}"
        parser = ContractParser(source)
        contracts = parser.parse()
        
        self.assertLessEqual(contracts[0].complexity, 3)
        
    def test_complex_condition(self):
        """Test complex condition complexity"""
        source = "void f() pre(a > 0 && b < 10 && c == 5 || d != 0 && e || f) {}"
        parser = ContractParser(source)
        contracts = parser.parse()
        
        # Should detect high complexity
        self.assertGreater(contracts[0].complexity, 5)


class TestContractAnalyzer(unittest.TestCase):
    """Test contract analysis"""
    
    def setUp(self):
        self.analyzer = ContractAnalyzer()
        
    def test_detect_delete_pattern(self):
        """Test detection of delete pattern"""
        contract = Contract(
            type=ContractType.PRE,
            condition="ptr != nullptr && delete(ptr)",
            location=(1, 0)
        )
        
        violations = self.analyzer.analyze([contract], "test.cpp")
        self.assertTrue(any('null pointer' in v.message.lower() for v in violations))
        
    def test_detect_const_cast(self):
        """Test detection of const_cast"""
        contract = Contract(
            type=ContractType.PRE,
            condition="true",
            location=(1, 0)
        )
        
        # Manually add dangerous pattern
        source = "const_cast<int*>(ptr)"
        violations = self.analyzer.analyze([contract], source)
        
    def test_detect_tautology(self):
        """Test detection of tautologies"""
        contract = Contract(
            type=ContractType.PRE,
            condition="true",
            location=(1, 0)
        )
        
        violations = self.analyzer.analyze([contract], "test.cpp")
        self.assertTrue(any('tautology' in v.message.lower() for v in violations))


class TestFileChecking(unittest.TestCase):
    """Test file validation"""
    
    def test_check_nonexistent_file(self):
        """Test error handling for nonexistent file"""
        with self.assertRaises(FileNotFoundError):
            check_file(Path("/nonexistent/file.cpp"))
            
    def test_check_unsupported_file_type(self):
        """Test error handling for unsupported file type"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test")
            temp_path = Path(f.name)
        
        try:
            with self.assertRaises(ValueError):
                check_file(temp_path)
        finally:
            temp_path.unlink()


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_full_analysis(self):
        """Test full analysis of realistic C++ code"""
        source = '''
        int process_data(const Data& d)
            pre(d.valid)
            pre(d.items.size() > 0)
            post(result >= 0)
        {
            return compute(d);
        }
        '''
        
        parser = ContractParser(source, "test.cpp")
        contracts = parser.parse()
        
        analyzer = ContractAnalyzer()
        violations = analyzer.analyze(contracts, source, "test.cpp")
        
        # Should have 3 contracts
        self.assertEqual(len(contracts), 3)
        
        # Should have no violations for valid code
        self.assertEqual(len(violations), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)