#!/bin/bash

# Kamikaze AI - CI/CD Pipeline Validation Script
# This script validates the CI/CD pipeline configuration and components

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation functions
validate_file_exists() {
    local file="$1"
    local description="$2"
    
    if [ -f "$PROJECT_ROOT/$file" ]; then
        log_success "$description exists: $file"
        return 0
    else
        log_error "$description missing: $file"
        return 1
    fi
}

validate_directory_exists() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        log_success "$description exists: $dir"
        return 0
    else
        log_error "$description missing: $dir"
        return 1
    fi
}

validate_yaml_syntax() {
    local file="$1"
    local description="$2"
    
    if command -v python3 >/dev/null 2>&1; then
        if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/$file'))" 2>/dev/null; then
            log_success "$description has valid YAML syntax: $file"
            return 0
        else
            log_error "$description has invalid YAML syntax: $file"
            return 1
        fi
    else
        log_warning "Python3 not available, skipping YAML validation for $file"
        return 0
    fi
}

validate_json_syntax() {
    local file="$1"
    local description="$2"
    
    if command -v python3 >/dev/null 2>&1; then
        if python3 -c "import json; json.load(open('$PROJECT_ROOT/$file'))" 2>/dev/null; then
            log_success "$description has valid JSON syntax: $file"
            return 0
        else
            log_error "$description has invalid JSON syntax: $file"
            return 1
        fi
    else
        log_warning "Python3 not available, skipping JSON validation for $file"
        return 0
    fi
}

validate_python_syntax() {
    local file="$1"
    local description="$2"
    
    if command -v python3 >/dev/null 2>&1; then
        if python3 -m py_compile "$PROJECT_ROOT/$file" 2>/dev/null; then
            log_success "$description has valid Python syntax: $file"
            return 0
        else
            log_error "$description has invalid Python syntax: $file"
            return 1
        fi
    else
        log_warning "Python3 not available, skipping Python validation for $file"
        return 0
    fi
}

# Main validation function
main() {
    log_info "Kamikaze AI CI/CD Pipeline Validation"
    log_info "====================================="
    
    local errors=0
    
    # Validate GitHub Actions workflows
    log_info "Validating GitHub Actions workflows..."
    validate_file_exists ".github/workflows/ci.yml" "CI workflow" || ((errors++))
    validate_file_exists ".github/workflows/deploy.yml" "Deployment workflow" || ((errors++))
    validate_file_exists ".github/workflows/security.yml" "Security workflow" || ((errors++))
    validate_file_exists ".github/workflows/monitoring.yml" "Monitoring workflow" || ((errors++))
    
    # Validate YAML syntax
    log_info "Validating YAML syntax..."
    validate_yaml_syntax ".github/workflows/ci.yml" "CI workflow" || ((errors++))
    validate_yaml_syntax ".github/workflows/deploy.yml" "Deployment workflow" || ((errors++))
    validate_yaml_syntax ".github/workflows/security.yml" "Security workflow" || ((errors++))
    validate_yaml_syntax ".github/workflows/monitoring.yml" "Monitoring workflow" || ((errors++))
    validate_yaml_syntax ".pre-commit-config.yaml" "Pre-commit configuration" || ((errors++))
    
    # Validate configuration files
    log_info "Validating configuration files..."
    validate_file_exists "config.json" "Application configuration" || ((errors++))
    validate_file_exists "requirements.txt" "Python requirements" || ((errors++))
    validate_file_exists "pytest.ini" "Pytest configuration" || ((errors++))
    validate_file_exists ".flake8" "Flake8 configuration" || ((errors++))
    validate_file_exists "Dockerfile" "Docker configuration" || ((errors++))
    
    # Validate JSON syntax
    log_info "Validating JSON syntax..."
    validate_json_syntax "config.json" "Application configuration" || ((errors++))
    
    # Validate Python files
    log_info "Validating Python syntax..."
    validate_python_syntax "app.py" "Main application" || ((errors++))
    
    # Validate test infrastructure
    log_info "Validating test infrastructure..."
    validate_directory_exists "tests" "Tests directory" || ((errors++))
    validate_file_exists "tests/__init__.py" "Tests package init" || ((errors++))
    validate_file_exists "tests/conftest.py" "Pytest configuration" || ((errors++))
    validate_file_exists "tests/test_config.py" "Configuration tests" || ((errors++))
    validate_file_exists "tests/test_api.py" "API tests" || ((errors++))
    validate_file_exists "tests/test_app.py" "Application tests" || ((errors++))
    
    # Validate scripts
    log_info "Validating deployment scripts..."
    validate_file_exists "scripts/deploy.sh" "Deployment script" || ((errors++))
    
    # Check if deployment script is executable
    if [ -f "$PROJECT_ROOT/scripts/deploy.sh" ]; then
        if [ -x "$PROJECT_ROOT/scripts/deploy.sh" ]; then
            log_success "Deployment script is executable"
        else
            log_warning "Deployment script is not executable (run: chmod +x scripts/deploy.sh)"
        fi
    fi
    
    # Validate environment configurations
    log_info "Validating environment configurations..."
    validate_file_exists ".github/environments/production.yml" "Production environment config" || ((errors++))
    validate_file_exists ".github/environments/staging.yml" "Staging environment config" || ((errors++))
    
    # Run basic tests if pytest is available
    log_info "Running basic tests..."
    if command -v python3 >/dev/null 2>&1 && python3 -c "import pytest" 2>/dev/null; then
        cd "$PROJECT_ROOT"
        if python3 -m pytest tests/test_config.py::TestConfigValidation::test_config_json_exists -v --tb=short; then
            log_success "Basic configuration test passed"
        else
            log_error "Basic configuration test failed"
            ((errors++))
        fi
    else
        log_warning "Pytest not available, skipping test execution"
    fi
    
    # Summary
    log_info "Validation Summary"
    log_info "=================="
    
    if [ $errors -eq 0 ]; then
        log_success "🎉 All validations passed! CI/CD pipeline is ready."
        echo ""
        log_info "Next steps:"
        log_info "1. Configure GitHub repository secrets"
        log_info "2. Set up AWS infrastructure (EC2, Secrets Manager)"
        log_info "3. Test the pipeline with a pull request"
        log_info "4. Monitor the first deployment"
        return 0
    else
        log_error "❌ $errors validation(s) failed. Please fix the issues above."
        echo ""
        log_info "Common fixes:"
        log_info "1. Ensure all required files are present"
        log_info "2. Check YAML/JSON syntax"
        log_info "3. Verify Python syntax"
        log_info "4. Install missing dependencies"
        return 1
    fi
}

# Execute main function
main "$@"
