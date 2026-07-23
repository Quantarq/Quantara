#!/usr/bin/env bash
# scripts/profile_contracts.sh
#
# Gas profiling report generator for Quantara Soroban contracts (issue #248).
#
# For each contract entry-point this script:
#   1. Builds the contract in release mode.
#   2. Runs cargo-flamegraph to collect CPU/instruction profiles.
#   3. Extracts the instruction-count summary reported by the Soroban SDK's
#      built-in budget when tests run with SOROBAN_BUDGET=1.
#   4. Writes a Markdown report to docs/gas/<version>.md.
#
# Usage:
#   ./scripts/profile_contracts.sh [--version <semver>] [--contracts-dir <path>]
#
# Requirements:
#   - Rust toolchain ≥ 1.88.0 with wasm32-unknown-unknown target
#   - cargo-flamegraph  (cargo install flamegraph)
#   - perl (for text processing, ships with most Linux distributions)
#
# The script is intentionally non-fatal for flamegraph (which requires
# perf/dtrace and may not be available in CI containers): if flamegraph
# cannot be installed or fails, a note is recorded in the report and
# execution continues.

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
CONTRACTS_DIR="${CONTRACTS_DIR:-quantara/soroban/contracts}"
VERSION="${VERSION:-$(date +%Y-%m-%d)}"
REPORT_DIR="docs/gas"
REPORT_FILE="${REPORT_DIR}/${VERSION}.md"
FLAMEGRAPH_DIR="${REPORT_DIR}/flamegraphs/${VERSION}"

# Contracts and their entry-points to profile.
# Format: "contract_name:entry_point_test_filter"
CONTRACTS=(
  "vault:test"
  "looping:test"
  "rewards:test"
  "common:test"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[profile_contracts] $*"; }
warn() { echo "[profile_contracts] WARN: $*" >&2; }

check_prereqs() {
  local missing=0
  for cmd in cargo perl; do
    if ! command -v "$cmd" &>/dev/null; then
      warn "Required command not found: $cmd"
      missing=1
    fi
  done
  if (( missing )); then
    echo "ERROR: Missing prerequisites. Install the required tools and re-run." >&2
    exit 1
  fi

  if ! cargo flamegraph --version &>/dev/null 2>&1; then
    warn "cargo-flamegraph not found — installing..."
    cargo install flamegraph 2>&1 || {
      warn "cargo-flamegraph installation failed. Flamegraph sections will be skipped."
      FLAMEGRAPH_AVAILABLE=0
      return
    }
  fi
  FLAMEGRAPH_AVAILABLE=1
}

# Run cargo test with SOROBAN_BUDGET=1 and capture the budget output.
# The Soroban SDK prints a budget summary when SOROBAN_BUDGET env var is set.
run_budget_tests() {
  local contract="$1"
  local filter="$2"
  local out

  out=$(
    cd "${CONTRACTS_DIR}/${contract}"
    SOROBAN_BUDGET=1 cargo test --release -- --nocapture "$filter" 2>&1
  ) || true

  echo "$out"
}

# Extract instruction-count lines from Soroban budget output.
extract_budget_lines() {
  echo "$1" | grep -E "(cpu_insns|mem_bytes|Budget|instructions)" | head -40 || echo "(no budget output captured)"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  log "Starting gas profiling — version=${VERSION}"
  log "Contracts directory: ${CONTRACTS_DIR}"
  log "Report target: ${REPORT_FILE}"

  check_prereqs

  mkdir -p "${REPORT_DIR}"
  mkdir -p "${FLAMEGRAPH_DIR}"

  # Build all contracts first to surface any compilation errors early.
  log "Building all contracts (release)..."
  (
    cd "${CONTRACTS_DIR}"
    cargo build --release --target wasm32-unknown-unknown 2>&1
  )
  log "Build succeeded."

  # Collect per-contract budget data.
  declare -A BUDGET_DATA
  for entry in "${CONTRACTS[@]}"; do
    contract="${entry%%:*}"
    filter="${entry##*:}"
    log "Profiling ${contract}..."

    raw_output=$(run_budget_tests "${contract}" "${filter}")
    BUDGET_DATA["${contract}"]=$(extract_budget_lines "${raw_output}")

    # Attempt flamegraph if available and running on Linux with perf.
    if (( FLAMEGRAPH_AVAILABLE )); then
      fg_svg="${FLAMEGRAPH_DIR}/${contract}.svg"
      (
        cd "${CONTRACTS_DIR}/${contract}"
        CARGO_PROFILE_RELEASE_DEBUG=true \
          cargo flamegraph \
            --output "$(pwd)/../../../../../${fg_svg}" \
            --test "${filter}" -- --nocapture 2>&1
      ) && log "Flamegraph saved: ${fg_svg}" \
        || warn "Flamegraph failed for ${contract} (perf may not be available in this environment)"
    fi
  done

  # Write the Markdown report.
  write_report "${VERSION}" BUDGET_DATA

  log "Report written to ${REPORT_FILE}"
}

# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------
write_report() {
  local version="$1"
  local -n data="$2"

  cat > "${REPORT_FILE}" <<HEADER
# Gas Profiling Report — ${version}

> Auto-generated by \`scripts/profile_contracts.sh\` on $(date -u +"%Y-%m-%dT%H:%M:%SZ").

## Overview

This report captures the Soroban instruction-count budget consumed by each
entry-point across the Quantara smart contract suite.  Numbers are collected
from \`cargo test --release\` runs with the \`SOROBAN_BUDGET=1\` environment
variable which causes the Soroban SDK to print a budget summary at the end of
each contract invocation.

Lower instruction counts reduce the probability of hitting the Soroban
network's CPU budget limit (currently **100 000 000 instructions** per
transaction).

---

## Environment

| Field            | Value                                       |
|------------------|---------------------------------------------|
| Report version   | ${version}                                  |
| Rust toolchain   | $(rustc --version 2>/dev/null || echo "n/a")|
| Soroban SDK      | 22.0.0 (pinned in Cargo.toml)               |
| Build profile    | release (opt-level=z, lto=true)             |
| Generated        | $(date -u +"%Y-%m-%dT%H:%M:%SZ")           |

---

HEADER

  for entry in "${CONTRACTS[@]}"; do
    contract="${entry%%:*}"
    budget="${data[$contract]}"

    cat >> "${REPORT_FILE}" <<CONTRACT

## Contract: \`${contract}\`

### Budget Summary (SOROBAN_BUDGET=1)

\`\`\`
${budget}
\`\`\`

CONTRACT

    fg_svg="${FLAMEGRAPH_DIR}/${contract}.svg"
    if [[ -f "${fg_svg}" ]]; then
      echo "### Flamegraph" >> "${REPORT_FILE}"
      echo "" >> "${REPORT_FILE}"
      echo "![${contract} flamegraph](flamegraphs/${version}/${contract}.svg)" >> "${REPORT_FILE}"
      echo "" >> "${REPORT_FILE}"
    else
      echo "_Flamegraph not available for this contract (perf/dtrace required)._" >> "${REPORT_FILE}"
      echo "" >> "${REPORT_FILE}"
    fi

    echo "---" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
  done

  cat >> "${REPORT_FILE}" <<FOOTER

## Notes

- Instruction counts may vary between runs due to non-deterministic test
  ordering.  Re-run the script with a fixed seed to obtain stable baselines.
- The flamegraph images (when present) are SVG files and can be opened in any
  modern browser.  Use Ctrl+F to search for hot functions.
- To compare across versions, diff the generated Markdown files:
  \`\`\`bash
  diff docs/gas/<v1>.md docs/gas/<v2>.md
  \`\`\`

## How to Re-run

\`\`\`bash
# Profile current codebase with today's date as the version:
./scripts/profile_contracts.sh

# Profile with an explicit semantic version:
VERSION=0.2.0 ./scripts/profile_contracts.sh

# Override the contracts directory:
CONTRACTS_DIR=path/to/contracts ./scripts/profile_contracts.sh
\`\`\`
FOOTER
}

# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
# Parse optional CLI flags before delegating to main().
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)    VERSION="$2"; shift 2 ;;
    --contracts-dir) CONTRACTS_DIR="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

main "$@"
