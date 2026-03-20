# Security Policy

🔐 Tailwind CSS Forge handles local files, build pipelines, and deployment credentials. Security is part of the product, not an afterthought.

## 🛡️ Supported Scope

Please report vulnerabilities related to:

- path traversal or unsafe filesystem access
- workspace isolation failures
- arbitrary command execution
- unsafe dependency installation behavior
- credential exposure
- weak encryption or secrets handling
- unsafe FTP/SFTP publishing behavior
- launcher or installer-ready distribution weaknesses
- API issues that could break local security guarantees

## 📣 Reporting a Vulnerability

Please do **not** open a public issue for a suspected security problem.

Instead, report it privately with:

- a clear description of the issue
- impact assessment
- reproduction steps
- proof of concept if available
- affected files or modules
- suggested mitigation if known

If no dedicated security inbox exists yet for the repository, use the repository owner’s private contact channel and label the report as `Security Report`.

## ⏱️ What to Expect

Security reports should be handled with this intent:

- prompt acknowledgment
- reproduction and triage
- fix development
- coordinated disclosure after a fix is available

Exact SLA values are not promised in this document, but valid reports should be treated as high priority.

## 🧱 Current Security Design

The current implementation already follows these principles:

- imported projects are copied into isolated workspaces
- original project files are not modified directly
- builds operate from workspace data
- publishing uses `dist` artifacts only
- secrets are stored locally with encryption
- build execution is constrained through internal allowlists
- launcher dependency installation avoids package lifecycle scripts in sensitive flows
- FTP publishing prefers explicit TLS and SFTP supports explicit host-key policy
- installer-ready validation checks staged layout integrity

## ⚠️ Responsible Disclosure

Please:

- avoid public disclosure before a fix is available
- avoid accessing data that is not yours
- avoid persistence, destructive actions, or lateral movement
- keep testing limited to what is necessary to prove the issue

## 🚫 Out of Scope

The following are generally out of scope unless they lead to a real security impact:

- purely theoretical issues without a practical exploit path
- missing best-practice headers in local-only development flows
- vulnerabilities in third-party tools without a project-specific exploit path
- denial of service based on unrealistic local misuse assumptions

## 🔄 Security Updates

When security-relevant fixes are made, related documentation and validation flows should be updated together when appropriate.

Thank you for helping keep Tailwind CSS Forge safe for local development and future desktop distribution.
