# Makefile for SysMon AI

.PHONY: help install dev-install test lint format clean run-dashboard run-evaluate

help:
	@echo "SysMon AI - Makefile Commands"
	@echo ""
	@echo "  install         Install package"
	@echo "  dev-install     Install with dev dependencies"
	@echo "  test            Run tests with coverage"
	@echo "  lint            Run linting checks"
	@echo "  format          Format code with black and isort"
	@echo "  clean           Clean build artifacts"
	@echo "  run-dashboard   Launch dashboard"
	@echo "  run-evaluate    Run evaluation"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ --cov=sysmon_ai --cov-report=term --cov-report=html

lint:
	flake8 sysmon_ai tests
	mypy sysmon_ai
	black --check sysmon_ai tests
	isort --check-only sysmon_ai tests

format:
	black sysmon_ai tests
	isort sysmon_ai tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-dashboard:
	sysmon dashboard

run-evaluate:
	sysmon evaluate --train-samples 100000 --test-samples 20000
