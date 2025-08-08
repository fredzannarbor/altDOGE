#!/usr/bin/env python3
"""
Setup script for the CFR Agency Document Counter.

This script provides a simple way to install and configure the tool.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        print(f"Current version: {sys.version}")
        return False
    return True


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False


def create_directories():
    """Create necessary directories."""
    directories = ["results", "logs"]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {directory}")


def run_tests():
    """Run tests to verify installation."""
    print("Running tests to verify installation...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("All tests passed! Installation verified.")
            return True
        else:
            print("Some tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("pytest not found. Skipping tests.")
        return True


def create_sample_csv():
    """Create a sample agencies CSV file for testing."""
    sample_csv = Path("sample_agencies.csv")
    
    if not sample_csv.exists():
        sample_data = """active,cfr_citation,parent_agency_name,agency_name,description
1,12 CFR 100-199,Treasury Department,Office of the Comptroller of the Currency,Banking regulation and supervision
1,13 CFR 200-299,Small Business Administration,Small Business Administration,Small business development and support
1,14 CFR 300-399,Transportation Department,Federal Aviation Administration,Aviation safety and regulation
0,15 CFR 400-499,Commerce Department,Bureau of Industry and Security,Export administration (inactive example)
"""
        
        with open(sample_csv, 'w') as f:
            f.write(sample_data)
        
        print(f"Created sample CSV file: {sample_csv}")


def show_usage_examples():
    """Show basic usage examples."""
    print("\n" + "="*60)
    print("INSTALLATION COMPLETE")
    print("="*60)
    print("\nBasic usage examples:")
    print("\n1. Test with sample data:")
    print("   python -m cfr_agency_counter.main sample_agencies.csv --limit 2")
    
    print("\n2. Validate configuration:")
    print("   python -m cfr_agency_counter.main sample_agencies.csv --validate-config")
    
    print("\n3. Dry run (no API calls):")
    print("   python -m cfr_agency_counter.main sample_agencies.csv --dry-run")
    
    print("\n4. Full processing with verbose output:")
    print("   python -m cfr_agency_counter.main your_agencies.csv --verbose")
    
    print("\n5. Get help:")
    print("   python -m cfr_agency_counter.main --help")
    
    print("\nDocumentation:")
    print("   README.md - Complete documentation")
    print("   EXAMPLES.md - Usage examples")
    print("   TROUBLESHOOTING.md - Troubleshooting guide")
    
    print("\nOutput will be saved to the 'results' directory.")
    print("Logs will be saved to 'cfr_agency_counter.log'.")


def main():
    """Main setup function."""
    print("CFR Agency Document Counter - Setup")
    print("="*40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("Setup failed during dependency installation.")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create sample CSV
    create_sample_csv()
    
    # Run tests
    if "--skip-tests" not in sys.argv:
        if not run_tests():
            print("Warning: Some tests failed. The tool may still work.")
    
    # Show usage examples
    show_usage_examples()


if __name__ == "__main__":
    main()