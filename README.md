# Multi-Agent OSINT Research System

A working multi-agent research pipeline using Python, Ollama and a local Qwen language model.

## Architecture

ResearchAgent -> AnalystAgent -> VerifierAgent -> ReviewerAgent

- ResearchAgent collects public HTTPS pages.
- AnalystAgent extracts claims with verbatim source quotations.
- VerifierAgent evaluates whether quotations support claims.
- ReviewerAgent produces the final assessment.
- AgentOrchestrator coordinates execution and records results.

## Requirements

- Python 3.10+
- Ollama
- Model: qwen3:30b-a3b-instruct-2507-q4_K_M

No paid search API is required.

## Run

    ollama pull qwen3:30b-a3b-instruct-2507-q4_K_M
    python3 run_agents.py https://www.python.org --pages 3
    python3 show_report.py

## Tests

    python3 -m unittest discover -p 'test_*.py' -v

## Reports

Each execution produces a JSON report containing source URLs, extracted claims, quotations, verification decisions and execution history.

Reports are stored in runs/ and excluded from Git.

## Verification limitations

Verification evaluates whether source quotations support extracted claims. It does not independently corroborate information across external sources.

## Demonstrated results

Successfully tested on real public pages from Python.org and Cloudflare.

## Purpose

A technical portfolio project demonstrating multi-agent orchestration, local LLM integration, evidence-based extraction, verification and automated testing.
