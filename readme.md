# Autonomous Agent Commerce Security Framework

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-green.svg)
![Tests: Passing](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)

A multi-layered security and governance framework designed to protect human principals in autonomous machine-to-machine AI economies. It decouples financial policy enforcement from probabilistic LLM reasoning to prevent algorithmic price collusion, identity spoofing, and late-night overspending.

---

## Technical Architecture

```text
                         [ HUMAN PRINCIPAL ]
                                  │
                      (Hardware Passkey / Key)
                                  │
                                  ▼
                   [ DELEGATION CREDENTIAL ENGINE ]
                       • HMAC-SHA256 Signatures
                       • Scoped Spending Limits
                       • Nonce & Expiration Epochs
                                  │
                                  ▼
                       [ BUYER AGENT RUNTIME ]
                                  │
       ┌──────────────────────────┴──────────────────────────┐
       │ 1. Sign Bid Token                                   │ 2. Submit Sealed Bid
       ▼                                                     ▼
[ CIRCUIT BREAKER WALLET ]                         [ SEALED-BID AUCTION ENGINE ]
 • Daily Velocity Tracker                           • Blind SHA-256 Commit Phase
 • Per-Tx Threshold Check                           • Asynchronous Reveal Window
 • Deterministic State Policy                       • Uniform Price Batch Match
       │                                                     │
       └──────────────────────────┬──────────────────────────┘
                                  │
                                  ▼
                   [ CRYPTOGRAPHIC SETTLEMENT ]
