"""Enhanced setup.py with comprehensive clean command and modern packaging."""

from setuptools import setup, find_packages, Command
import os
import glob
import shutil
import subprocess
from pathlib import Path

class CleanCommand(Command):
    """Custom clean command to remove all temporary and generated files."""
    
    description = 'Clean all temporary files, logs, outputs, and build artifacts'
    user_options = [
        ('all', 'a', 'Remove all possible temporary files'),
        ('logs', 'l', 'Remove only log files'),
        ('outputs', 'o', 'Remove only generated output files'),
        ('build', 'b', 'Remove only build artifacts'),
    ]
    
    def initialize_options(self):
        self.all = False
        self.logs = False
        self.outputs = False
        self.build = False
    
    def finalize_options(self):
        # If no specific option is chosen, default to all
        if not any([self.logs, self.outputs, self.build]):
            self.all = True
    
    def run(self):
        """Remove temporary files based on options."""
        removed_files = []
        removed_dirs = []
        
        # Define patterns for different categories
        patterns = {
            'logs': [
                '*.log',
                'slide_extract*.log',
                'script_run.log',
            ],
            'outputs': [
                '*_summary.md',
                '*_notes.md',
                '*_analysis.md',
                '.slide_extract_progress*.json',
                '.slide_dir_extract_manifest.txt',
                '.slide_dir_extract_progress.json',
            ],
            'build': [
                '**/__pycache__',
                '**/*.pyc',
                '**/*.pyo',
                '*.egg-info/',
                'build/',
                'dist/',
                '.eggs/',
                'htmlcov/',
                '.coverage',
                '.coverage.*',
                '.pytest_cache/',
                '.tox/',
                'venv/',
                '.venv/',
            ]
        }
        
        # Determine what to clean
        categories_to_clean = []
        if self.all:
            categories_to_clean = ['logs', 'outputs', 'build']
        else:
            if self.logs:
                categories_to_clean.append('logs')
            if self.outputs:
                categories_to_clean.append('outputs')
            if self.build:
                categories_to_clean.append('build')
        
        # Clean selected categories
        for category in categories_to_clean:
            print(f"Cleaning {category} files...")
            
            for pattern in patterns[category]:
                for path in glob.glob(pattern, recursive=True):
                    path_obj = Path(path)
                    
                    # Skip files in tests/fixtures (these are intentional test data)
                    if 'tests/fixtures' in str(path_obj):
                        continue
                    
                    try:
                        if path_obj.is_file():
                            path_obj.unlink()
                            removed_files.append(str(path_obj))
                        elif path_obj.is_dir():
                            shutil.rmtree(path_obj)
                            removed_dirs.append(str(path_obj))
                    except Exception as e:
                        print(f"Warning: Could not remove {path}: {e}")
        
        # Additional cleanup for specific build tools
        if 'build' in categories_to_clean:
            try:
                # Clean pytest cache
                if Path('.pytest_cache').exists():
                    shutil.rmtree('.pytest_cache')
                    removed_dirs.append('.pytest_cache')
                
                # Clean coverage files
                for cov_file in glob.glob('.coverage*'):
                    if Path(cov_file).is_file():
                        Path(cov_file).unlink()
                        removed_files.append(cov_file)
                        
            except Exception as e:
                print(f"Warning during build cleanup: {e}")
        
        # Summary
        print(f"\nCleanup Summary:")
        print(f"  Removed {len(removed_files)} files")
        print(f"  Removed {len(removed_dirs)} directories")
        
        if removed_files:
            print(f"\nRemoved files:")
            for f in sorted(removed_files):
                print(f"  - {f}")
        
        if removed_dirs:
            print(f"\nRemoved directories:")
            for d in sorted(removed_dirs):
                print(f"  - {d}")

class TestCommand(Command):
    """Custom test command with comprehensive testing."""
    
    description = 'Run comprehensive test suite'
    user_options = [
        ('unit', 'u', 'Run only unit tests'),
        ('integration', 'i', 'Run only integration tests'),
        ('coverage', 'c', 'Run tests with coverage report'),
        ('verbose', 'v', 'Verbose test output'),
    ]
    
    def initialize_options(self):
        self.unit = False
        self.integration = False
        self.coverage = False
        self.verbose = False
    
    def finalize_options(self):
        pass
    
    def run(self):
        """Run tests based on options."""
        try:
            import pytest
        except ImportError:
            print("pytest is required to run tests. Install with: pip install pytest")
            return 1
        
        args = []
        
        # Determine test scope
        if self.unit and not self.integration:
            args.append('tests/unit/')
        elif self.integration and not self.unit:
            args.append('tests/integration/')
        else:
            args.append('tests/')
        
        # Add coverage if requested
        if self.coverage:
            args.extend(['--cov=slide_extract', '--cov-report=html', '--cov-report=term'])
        
        # Add verbosity
        if self.verbose:
            args.append('-v')
        
        # Run tests
        exit_code = pytest.main(args)
        
        if self.coverage:
            print("\nCoverage report generated in htmlcov/index.html")
        
        return exit_code

# Read long description from README
def read_long_description():
    try:
        with open("README.md", "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "AI-powered presentation slide analysis and note generation tool"

# Read requirements
def read_requirements():
    try:
        with open("requirements.txt", "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return [
            "PyMuPDF>=1.23.0",
            "PyYAML>=6.0",
            "openai>=1.0.0",
            "anthropic>=0.7.0",
            "google-generativeai>=0.3.0",
            "httpx>=0.24.0",
            "Pillow>=10.0.0",
        ]

def read_dev_requirements():
    try:
        with open("requirements-dev.txt", "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return [
            "pytest>=7.4.0",
            "pytest-mock>=3.11.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "pylint>=2.17.0",
        ]

setup(
    name="slide-extract",
    version="1.1.0",
    author="slide-extract contributors",
    author_email="contributors@slide-extract.example.com",
    description="AI-powered presentation slide analysis and note generation with resume capability",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/slide-extract",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Education",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Markup :: Markdown",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": read_dev_requirements(),
        "test": [
            "pytest>=7.4.0",
            "pytest-mock>=3.11.0", 
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "slide-extract=slide_extract.cli.single:main",
            "slide-dir-extract=slide_extract.cli.batch:main",
        ],
    },
    cmdclass={
        "clean": CleanCommand,
        "test": TestCommand,
    },
    include_package_data=True,
    package_data={
        "slide_extract": ["prompts/*.md"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/slide-extract/issues",
        "Source": "https://github.com/yourusername/slide-extract",
        "Documentation": "https://github.com/yourusername/slide-extract#readme",
    },
)