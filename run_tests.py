"""
Automated Test Runner for AI Video Meeting Intelligence Assistant
Usage:
    python run_tests.py          # Run all tests (backend + E2E)
    python run_tests.py --backend # Run backend unit/integration tests
    python run_tests.py --e2e     # Run Playwright browser E2E tests
"""
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="AI Video Assistant Test Runner")
    parser.add_argument("--backend", action="store_true", help="Run backend tests only")
    parser.add_argument("--e2e", action="store_true", help="Run Playwright E2E browser tests only")
    args = parser.parse_args()

    python_bin = sys.executable

    cmd = [python_bin, "-m", "pytest", "-v"]

    if args.backend:
        cmd.append("tests/test_backend.py")
    elif args.e2e:
        cmd.append("tests/test_e2e_playwright.py")
    else:
        cmd.append("tests")

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
