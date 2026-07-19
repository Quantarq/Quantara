# Security Policy

## Reporting a Vulnerability

We take the security of Quantara seriously. If you discover a security vulnerability,
please report it responsibly.

**Do not** report security vulnerabilities through public GitHub issues.

Instead, please email us at: **security@quantara.protocol**

## Response SLA

| Stage | Timeline |
| --- | --- |
| Acknowledgement | 48 hours |
| Initial assessment | 5 business days |
| Fix release (critical/high) | 30 days |
| Fix release (medium/low) | 90 days |

## Bounty Scope

### In Scope

- Soroban smart contracts (reentrancy, integer overflow, access control, logic flaws)
- FastAPI backend (auth bypass, injection, IDOR, RCE)
- React frontend (XSS, wallet injection, sensitive data exposure)
- Docker / CI pipeline (secret leakage, supply chain)
- API keys or private keys exposed in the repository

### Out of Scope

- Denial of service attacks
- Social engineering
- Vulnerabilities in third-party dependencies (report upstream)
- Issues requiring physical access to a user's device

## Supported Versions

| Version | Supported |
| --- | --- |
| Latest | :white_check_mark: |

## Responsible Disclosure

We request that you:
- Give us reasonable time to fix the issue before public disclosure
- Make a good faith effort to avoid privacy violations and data destruction
- Do not exploit the vulnerability beyond what is necessary to demonstrate the issue
