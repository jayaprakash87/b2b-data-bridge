# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-03-30

### Added
- Outbound pipeline: export products, pricing, and stock as CSV/XLSX files
- Inbound pipeline: download, parse, validate, and save orders from distributor
- sFTP client with automatic retry and exponential backoff
- Local filesystem transport for development and testing
- EAN/GTIN validation using GS1 check-digit algorithm
- Field-level validation for all data types
- Filename pattern validation (`PREFIX_YYYYMMDD_HHMMSS.ext`)
- Duplicate order detection (idempotent reprocessing)
- Bad file quarantine with reason logging
- CSV delimiter `;` (European/Swiss standard)
- XLSX read/write support
- YAML configuration with `.env` override for secrets
- CLI with `init`, `outbound`, `inbound` commands and `--local` flag
- Standalone binary build via PyInstaller
- 78 automated tests
- Comprehensive documentation:
  - Architecture diagrams (Mermaid)
  - File Format Specification (ICD)
  - sFTP Connectivity Setup Guide
  - Integration Test Plan (12 UAT scenarios)
  - Go-Live Runbook
  - Client Quick Start Guide
  - Project Proposal / Statement of Work
- Sample CSV files for all data types

### Security
- SSH host key verification (RejectPolicy — prevents MITM attacks)
- SSH key authentication support (preferred over password)
- Path traversal protection on file downloads
- Credential masking in logs and tracebacks (`SftpConfig.__repr__`)
- Row count limit (500K) to prevent memory exhaustion
- Inbound file count cap (100 per poll cycle)
- Retry ceiling (max 10 retries, 5-minute backoff cap)
