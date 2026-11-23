# DeleGate // Rune Rust Terminal Companion Client

The **Rune Client** is a lightweight, asynchronous command-line tool written in Rust designed to interact with the DeleGate Stage-Gate task management platform. It allows developers and operations team members to inspect active stage-gates, poll open tasks from the collaborative pool, and atomically claim tasks directly from their terminal.

---

## Architecture Overview

The Rune Client connects to DeleGate's Django JSON API endpoints:

- `GET /home/api/pool/`: Queries open, unclaimed tasks in active Stage-Gates using optimized SQL Subqueries and `select_related` table joins.
- `POST /home/api/tasks/<task_id>/mine/`: Performs atomic task acquisition wrapped in database transactions (`select_for_update`) while strictly enforcing:
  - Worker single-active-task constraint (unless the task has `is_multiclaimable = true`).
  - Stage-Gate unlocking requirements (tasks in locked downstream gates cannot be mined).
- `POST /home/api/gates/<gate_id>/pass/`: Enforces the Stage-Gate exit rule (100% of tasks in the gate must be completed before passing and unlocking Gate $N+1$).

---

## Setup & Compilation

### Prerequisites
- [Rust & Cargo](https://rustup.rs/) (1.70+ recommended)
- Running DeleGate Django server (default: `http://127.0.0.1:8080`)

### Building the Binary
```bash
cd rune_client
cargo build --release
```

The compiled binary will be located at `target/release/rune_client`.

---

## Usage

### 1. View Pool Status & Available Tasks
```bash
cargo run -- status
# Or with release binary:
./target/release/rune_client status
```

### 2. Mine an Available Task
```bash
cargo run -- mine <TASK_ID>
# Example:
cargo run -- mine 4
```

### 3. Approve and Pass a Stage Gate (Manager Sign-off)
```bash
cargo run -- pass-gate <GATE_ID>
```

### Configuration Options
- Specify a custom DeleGate server:
  ```bash
  cargo run -- --server http://192.168.1.100:8080 status
  ```
- Or set environment variables:
  ```bash
  export DELEGATE_SERVER_URL="http://127.0.0.1:8080"
  export DELEGATE_USER="x3n0"
  ```
