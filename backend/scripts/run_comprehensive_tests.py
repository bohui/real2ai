#!/usr/bin/env python3
"""
Comprehensive test runner script with enhanced reporting.
"""
import asyncio
import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class ComprehensiveTestRunner:
    """Run comprehensive tests with detailed reporting."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.reports_dir = self.project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_command(self, command: List[str], description: str) -> Dict[str, Any]:
        """Run a command and capture results."""
        print(f"\n🔍 {description}")
        print(f"Running: {' '.join(command)}")
        
        start_time = datetime.now()
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "command": ' '.join(command),
                "description": description,
                "success": result.returncode == 0,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "timestamp": start_time.isoformat()
            }
        except subprocess.TimeoutExpired:
            return {
                "command": ' '.join(command),
                "description": description,
                "success": False,
                "duration": 300,
                "stdout": "",
                "stderr": "Command timed out after 5 minutes",
                "return_code": -1,
                "timestamp": start_time.isoformat()
            }
        except Exception as e:
            return {
                "command": ' '.join(command),
                "description": description,
                "success": False,
                "duration": 0,
                "stdout": "",
                "stderr": str(e),
                "return_code": -2,
                "timestamp": start_time.isoformat()
            }

    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests with coverage."""
        return self.run_command([
            "python", "-m", "pytest",
            "tests/unit/",
            "-v",
            "--cov=app",
            "--cov-report=html:test_reports/unit_coverage_html",
            "--cov-report=xml:test_reports/unit_coverage.xml",
            "--cov-report=term-missing",
            "--junit-xml=test_reports/unit_results.xml",
            "-m", "unit"
        ], "Unit Tests with Coverage")

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        return self.run_command([
            "python", "-m", "pytest",
            "tests/integration/",
            "-v",
            "--junit-xml=test_reports/integration_results.xml",
            "-m", "integration"
        ], "Integration Tests")

    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarks."""
        return self.run_command([
            "python", "-m", "pytest",
            "tests/performance/",
            "-v",
            "--junit-xml=test_reports/performance_results.xml",
            "-m", "not slow"  # Skip slow tests by default
        ], "Performance Tests")

    def run_security_tests(self) -> Dict[str, Any]:
        """Run security vulnerability tests."""
        return self.run_command([
            "python", "-m", "pytest",
            "tests/security/",
            "-v",
            "--junit-xml=test_reports/security_results.xml"
        ], "Security Tests")

    def run_linting(self) -> Dict[str, Any]:
        """Run code linting."""
        return self.run_command([
            "python", "-m", "flake8",
            "app/",
            "--max-line-length=88",
            "--extend-ignore=E203,W503",
            "--output-file=test_reports/flake8_report.txt"
        ], "Code Linting (Flake8)")

    def run_type_checking(self) -> Dict[str, Any]:
        """Run type checking with mypy."""
        return self.run_command([
            "python", "-m", "mypy",
            "app/",
            "--config-file=pyproject.toml",
            "--junit-xml=test_reports/mypy_results.xml"
        ], "Type Checking (MyPy)")

    def check_dependencies(self) -> Dict[str, Any]:
        """Check for dependency vulnerabilities."""
        return self.run_command([
            "python", "-m", "safety", "check",
            "--json",
            "--output", "test_reports/safety_report.json"
        ], "Dependency Security Check")

    def generate_summary_report(self, results: List[Dict[str, Any]]) -> None:
        """Generate comprehensive summary report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Calculate summary statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['success'])
        failed_tests = total_tests - passed_tests
        total_duration = sum(r['duration'] for r in results)
        
        summary = {
            "test_run_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_test_suites": total_tests,
                "passed_suites": passed_tests,
                "failed_suites": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
                "total_duration_seconds": round(total_duration, 2),
                "total_duration_formatted": self.format_duration(total_duration)
            },
            "detailed_results": results
        }
        
        # Save JSON report
        json_report_path = self.reports_dir / f"test_summary_{timestamp}.json"
        with open(json_report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Generate HTML report
        self.generate_html_report(summary, timestamp)
        
        # Print summary to console
        self.print_console_summary(summary)
        
        print(f"\n📊 Detailed reports saved to: {self.reports_dir}")
        print(f"📋 JSON Summary: {json_report_path}")

    def generate_html_report(self, summary: Dict[str, Any], timestamp: str) -> None:
        """Generate HTML test report."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real2.AI Test Report - {timestamp}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; }}
        .header {{ background: #2563eb; color: white; padding: 20px; border-radius: 8px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6; }}
        .metric h3 {{ margin: 0 0 10px 0; color: #374151; }}
        .metric .value {{ font-size: 2rem; font-weight: bold; color: #1f2937; }}
        .results {{ margin-top: 30px; }}
        .test-result {{ background: white; border: 1px solid #e5e7eb; margin: 10px 0; border-radius: 8px; overflow: hidden; }}
        .test-header {{ padding: 15px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }}
        .success {{ border-left: 4px solid #10b981; }}
        .failure {{ border-left: 4px solid #ef4444; }}
        .test-details {{ padding: 15px; }}
        .success-rate {{ color: #059669; }}
        .failure-rate {{ color: #dc2626; }}
        pre {{ background: #f3f4f6; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Real2.AI Comprehensive Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Test Suites</h3>
            <div class="value">{summary['test_run_summary']['total_test_suites']}</div>
        </div>
        <div class="metric">
            <h3>Success Rate</h3>
            <div class="value success-rate">{summary['test_run_summary']['success_rate']}</div>
        </div>
        <div class="metric">
            <h3>Total Duration</h3>
            <div class="value">{summary['test_run_summary']['total_duration_formatted']}</div>
        </div>
        <div class="metric">
            <h3>Failed Suites</h3>
            <div class="value failure-rate">{summary['test_run_summary']['failed_suites']}</div>
        </div>
    </div>
    
    <div class="results">
        <h2>Detailed Results</h2>
        """
        
        for result in summary['detailed_results']:
            status_class = "success" if result['success'] else "failure"
            status_text = "✅ PASSED" if result['success'] else "❌ FAILED"
            
            html_content += f"""
        <div class="test-result {status_class}">
            <div class="test-header">
                <h3>{result['description']} - {status_text}</h3>
                <p>Duration: {result['duration']:.2f}s | Command: <code>{result['command']}</code></p>
            </div>
            """
            
            if not result['success']:
                html_content += f"""
            <div class="test-details">
                <h4>Error Output:</h4>
                <pre>{result['stderr']}</pre>
            </div>
            """
            
            html_content += "</div>"
        
        html_content += """
    </div>
</body>
</html>
        """
        
        html_report_path = self.reports_dir / f"test_report_{timestamp}.html"
        with open(html_report_path, 'w') as f:
            f.write(html_content)
        
        print(f"📱 HTML Report: {html_report_path}")

    def print_console_summary(self, summary: Dict[str, Any]) -> None:
        """Print test summary to console."""
        print("\n" + "="*80)
        print("🧪 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("="*80)
        
        test_summary = summary['test_run_summary']
        print(f"📊 Total Test Suites: {test_summary['total_test_suites']}")
        print(f"✅ Passed: {test_summary['passed_suites']}")
        print(f"❌ Failed: {test_summary['failed_suites']}")
        print(f"📈 Success Rate: {test_summary['success_rate']}")
        print(f"⏱️  Total Duration: {test_summary['total_duration_formatted']}")
        
        print(f"\n📋 DETAILED RESULTS:")
        for result in summary['detailed_results']:
            status = "✅" if result['success'] else "❌"
            duration = f"{result['duration']:.2f}s"
            print(f"{status} {result['description']:<35} ({duration})")
            
            if not result['success'] and result['stderr']:
                # Print first few lines of error
                error_lines = result['stderr'].split('\n')[:3]
                for line in error_lines:
                    if line.strip():
                        print(f"   💥 {line.strip()}")
        
        print("="*80)

    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def run_all_tests(self) -> None:
        """Run all test suites and generate comprehensive report."""
        print("🚀 Starting Comprehensive Test Suite for Real2.AI Backend")
        print(f"📁 Project Root: {self.project_root}")
        print(f"📂 Reports Directory: {self.reports_dir}")
        
        # Test execution order (dependencies first)
        test_functions = [
            self.run_linting,
            self.run_type_checking,
            self.check_dependencies,
            self.run_unit_tests,
            self.run_integration_tests,
            self.run_security_tests,
            self.run_performance_tests
        ]
        
        results = []
        for test_func in test_functions:
            result = test_func()
            results.append(result)
            
            # Print immediate result
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            duration = f"{result['duration']:.2f}s"
            print(f"{status} {result['description']} ({duration})")
            
            # Stop on critical failures (linting, type checking)
            if not result['success'] and test_func in [self.run_linting, self.run_type_checking]:
                print(f"⚠️  Critical test failed: {result['description']}")
                print("   Fix these issues before proceeding with other tests.")
                break
        
        # Generate comprehensive report
        self.generate_summary_report(results)
        
        # Determine overall success
        overall_success = all(r['success'] for r in results)
        exit_code = 0 if overall_success else 1
        
        if overall_success:
            print("\n🎉 ALL TESTS PASSED! Your code is ready for deployment.")
        else:
            print(f"\n⚠️  {sum(1 for r in results if not r['success'])} test suite(s) failed. Please review and fix.")
        
        sys.exit(exit_code)


def main():
    """Main entry point."""
    runner = ComprehensiveTestRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main()