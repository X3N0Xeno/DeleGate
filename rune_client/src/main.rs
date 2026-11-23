use clap::{Parser, Subcommand};
use colored::*;
use serde::{Deserialize, Serialize};
use std::env;

#[derive(Parser, Debug)]
#[command(name = "delegate")]
#[command(about = "Solarpunk Terminal Companion for DeleGate Stage-Gate Governance", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    #[arg(short, long, default_value = "http://127.0.0.1:8080")]
    server: String,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Inspect open pool tasks and project progression
    Status,
    /// Mine an open task from the active Stage-Gate pool
    Mine {
        /// Unique integer ID of the task to claim
        task_id: u32,
    },
    /// Approve and pass an unlocked stage-gate (Manager only, 100% completion required)
    PassGate {
        /// Unique integer ID of the StageGate
        gate_id: u32,
    },
}

#[derive(Debug, Deserialize, Serialize)]
struct GateInfo {
    id: Option<u32>,
    order: Option<u32>,
    name: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct ProjectInfo {
    id: Option<u32>,
    name: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct TaskItem {
    id: u32,
    title: String,
    description: String,
    effort_points: u32,
    priority: String,
    status: String,
    is_multiclaimable: bool,
    gate: GateInfo,
    project: ProjectInfo,
    created_by: String,
    claimed_by: Option<String>,
    due_date: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct PoolResponse {
    status: String,
    count: usize,
    project: Option<String>,
    tasks: Vec<TaskItem>,
}

#[derive(Debug, Deserialize, Serialize)]
struct MineResponse {
    status: String,
    message: String,
}

fn print_banner() {
    println!("{}", "================================================================".green());
    println!("{}", "   🌿  DeleGate // Rune Rust Terminal Companion v1.0".bright_green().bold());
    println!("{}", "   Stage-Gate Governance & Solarpunk Collaborative Mining".cyan());
    println!("{}", "================================================================".green());
}

async fn fetch_status(base_url: &str) -> Result<(), Box<dyn std::error::Error>> {
    let url = format!("{}/home/api/pool/", base_url.trim_end_matches('/'));
    println!("Connecting to {} ...", url.dimmed());

    let client = reqwest::Client::new();
    let res = client.get(&url).send().await?;

    if !res.status().is_success() {
        eprintln!("{} Failed to fetch pool (HTTP {})", "ERROR:".red().bold(), res.status());
        return Ok(());
    }

    let data: PoolResponse = res.json().await?;
    let proj_name = data.project.unwrap_or_else(|| "DeleGate Core".to_string());

    println!("\n{} {}", "Project:".bold(), proj_name.bright_green().bold());
    println!("{} {} open task(s) ready for mining\n", "Status:".bold(), data.count.to_string().yellow().bold());

    if data.tasks.is_empty() {
        println!("{}", "No tasks currently open to mine in active gates.".italic().dimmed());
        println!("{}", "Work moves through gates: check back once a gate clears or a new task is dispatched.\n".dimmed());
        return Ok(());
    }

    println!("{:<6} {:<4} {:<40} {:<6} {:<10} {:<14}", "ID".bold(), "GATE".bold(), "TASK TITLE".bold(), "PTS".bold(), "PRIORITY".bold(), "FLAGS".bold());
    println!("{}", "--------------------------------------------------------------------------------".dimmed());

    for task in data.tasks {
        let gate_code = format!("G{}", task.gate.order.unwrap_or(1));
        let prio_colored = match task.priority.as_str() {
            "CRIT" => "CRITICAL".red().bold(),
            "HIGH" => "HIGH".yellow().bold(),
            "MED" => "MEDIUM".cyan(),
            _ => "LOW".dimmed(),
        };

        let flags = if task.is_multiclaimable {
            "[Multi-Claim]".magenta()
        } else {
            "Single-Slot".dimmed()
        };

        let title_truncated = if task.title.len() > 38 {
            format!("{}...", &task.title[..35])
        } else {
            task.title
        };

        println!(
            "{:<6} {:<4} {:<40} {:<6} {:<10} {:<14}",
            task.id.to_string().green(),
            gate_code.bright_yellow(),
            title_truncated,
            task.effort_points.to_string().cyan(),
            prio_colored,
            flags
        );
    }

    println!("\n{} Run `{}` to claim a task.\n", "TIP:".bright_green().bold(), "delegate mine <task_id>".cyan());
    Ok(())
}

async fn mine_task(base_url: &str, task_id: u32) -> Result<(), Box<dyn std::error::Error>> {
    let url = format!("{}/home/api/tasks/{}/mine/", base_url.trim_end_matches('/'), task_id);
    println!("Acquiring task #{} from {} ...", task_id, url.dimmed());

    let client = reqwest::Client::new();
    let res = client
        .post(&url)
        .header("X-User", env::var("DELEGATE_USER").unwrap_or_else(|_| "admin".to_string()))
        .send()
        .await?;

    let status_code = res.status();
    let body_text = res.text().await?;

    if status_code.is_success() {
        if let Ok(resp) = serde_json::from_str::<MineResponse>(&body_text) {
            println!("{} {}", "SUCCESS:".green().bold(), resp.message.bright_green());
        } else {
            println!("{} Task #{} claimed successfully.", "SUCCESS:".green().bold(), task_id);
        }
    } else {
        if let Ok(err) = serde_json::from_str::<MineResponse>(&body_text) {
            eprintln!("{} {}", "CLAIM REJECTED:".red().bold(), err.message.yellow());
        } else {
            eprintln!("{} HTTP {} - {}", "ERROR:".red().bold(), status_code, body_text);
        }
    }

    Ok(())
}

async fn pass_gate(base_url: &str, gate_id: u32) -> Result<(), Box<dyn std::error::Error>> {
    let url = format!("{}/home/api/gates/{}/pass/", base_url.trim_end_matches('/'), gate_id);
    println!("Approving StageGate #{} at {} ...", gate_id, url.dimmed());

    let client = reqwest::Client::new();
    let res = client
        .post(&url)
        .header("X-User", env::var("DELEGATE_USER").unwrap_or_else(|_| "admin".to_string()))
        .send()
        .await?;

    let status_code = res.status();
    let body_text = res.text().await?;

    if status_code.is_success() {
        if let Ok(resp) = serde_json::from_str::<MineResponse>(&body_text) {
            println!("{} {}", "GATE PASSED:".green().bold(), resp.message.bright_green());
        } else {
            println!("{} Gate #{} approved and passed.", "SUCCESS:".green().bold(), gate_id);
        }
    } else {
        if let Ok(err) = serde_json::from_str::<MineResponse>(&body_text) {
            eprintln!("{} {}", "GATE APPROVAL BLOCKED:".red().bold(), err.message.yellow());
        } else {
            eprintln!("{} HTTP {} - {}", "ERROR:".red().bold(), status_code, body_text);
        }
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    let base_url = env::var("DELEGATE_SERVER_URL").unwrap_or(cli.server);

    print_banner();

    match cli.command {
        Some(Commands::Mine { task_id }) => {
            mine_task(&base_url, task_id).await?;
        }
        Some(Commands::PassGate { gate_id }) => {
            pass_gate(&base_url, gate_id).await?;
        }
        Some(Commands::Status) | None => {
            fetch_status(&base_url).await?;
        }
    }

    Ok(())
}
