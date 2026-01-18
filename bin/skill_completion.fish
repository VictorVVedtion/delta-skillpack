# Fish completion script for Delta SkillPack CLI
# Usage: source bin/skill_completion.fish
# Or copy to ~/.config/fish/completions/skill.fish

# Main commands
set -l commands doctor list hello plan implement ui run pipeline history show ralph

# Ralph subcommands
set -l ralph_commands init status start next-story story-status execute-pipeline mark-failed cancel

# Skill names
set -l skill_names plan implement ui review verify

# Disable file completion by default
complete -c skill -f

# Main commands
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "doctor" -d "Check environment and list available skills"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "list" -d "List available skills/workflows"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "hello" -d "Print a friendly greeting"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "plan" -d "Generate implementation plans"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "implement" -d "Implement a selected plan"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "ui" -d "Generate UI specification"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "run" -d "Run any workflow by name"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "pipeline" -d "Run multiple skills in sequence"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "history" -d "Show recent skill runs"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "show" -d "Show details of a specific run"
complete -c skill -n "not __fish_seen_subcommand_from $commands" -a "ralph" -d "PRD-driven autonomous development"

# Ralph subcommands
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "init" -d "Initialize PRD from task description"
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "status" -d "Show current PRD execution status"
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "start" -d "Start Ralph automation loop"
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "next-story" -d "Get next story to execute"
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "story-status" -d "Get status of a specific story"
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "execute-pipeline" -d "Execute skill pipeline for a story"
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "mark-failed" -d "Mark a story as failed"
complete -c skill -n "__fish_seen_subcommand_from ralph; and not __fish_seen_subcommand_from $ralph_commands" -a "cancel" -d "Cancel current Ralph loop"

# Run command - skill names
complete -c skill -n "__fish_seen_subcommand_from run" -a "$skill_names"

# Common options for plan/implement/ui/run
complete -c skill -n "__fish_seen_subcommand_from plan implement ui run" -s f -l plan-file -d "Plan file input" -r -F
complete -c skill -n "__fish_seen_subcommand_from plan implement ui run" -l dry-run -d "Show what would run"
complete -c skill -n "__fish_seen_subcommand_from plan implement ui run" -l notebook -d "NotebookLM notebook ID" -r
complete -c skill -n "__fish_seen_subcommand_from plan implement ui run" -l no-knowledge -d "Disable knowledge queries"

# Implement specific options
complete -c skill -n "__fish_seen_subcommand_from implement" -s i -l interactive -d "Interactively select plan"

# History options
complete -c skill -n "__fish_seen_subcommand_from history" -s n -l limit -d "Number of runs to show" -a "5 10 20 50"

# Ralph init options
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from init" -s f -l prd-file -d "Use existing PRD JSON file" -r -F

# Ralph status/next-story options
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from status next-story story-status" -l json -d "Output as JSON"

# Ralph start options
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from start" -s n -l max-iterations -d "Maximum iterations" -a "10 50 100 200"
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from start" -l dry-run -d "Show what would run"

# Ralph story-status options
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from story-status" -l story-id -d "Story ID to check" -r

# Ralph execute-pipeline options
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from execute-pipeline" -l story-id -d "Story ID to execute" -r
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from execute-pipeline" -l steps -d "Comma-separated steps" -a "plan,implement plan,implement,review plan,implement,review,verify"

# Ralph mark-failed options
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from mark-failed" -l story-id -d "Story ID to mark" -r
complete -c skill -n "__fish_seen_subcommand_from ralph; and __fish_seen_subcommand_from mark-failed" -l error -d "Error message" -r
