#compdef skill
# Zsh completion script for Delta SkillPack CLI
# Usage: source bin/skill_completion.zsh
# Or add to ~/.zshrc: fpath=(/path/to/delta-skillpack/bin $fpath) && compinit

_skill() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '1: :->command' \
        '*: :->args'

    case $state in
        command)
            local commands=(
                'doctor:Check environment and list available skills'
                'list:List available skills/workflows'
                'hello:Print a friendly greeting'
                'plan:Generate implementation plans'
                'implement:Implement a selected plan'
                'ui:Generate UI specification'
                'run:Run any workflow by name'
                'pipeline:Run multiple skills in sequence'
                'history:Show recent skill runs'
                'show:Show details of a specific run'
                'ralph:PRD-driven autonomous development'
            )
            _describe -t commands 'skill commands' commands
            ;;
        args)
            case $line[1] in
                ralph)
                    _skill_ralph
                    ;;
                run)
                    _skill_run
                    ;;
                plan|implement|ui)
                    _skill_common_options
                    ;;
                pipeline)
                    _arguments \
                        '--dry-run[Show what would run without executing]' \
                        '*: :_skill_names'
                    ;;
                history)
                    _arguments \
                        '-n[Number of runs to show]:limit:(5 10 20 50)' \
                        '--limit[Number of runs to show]:limit:(5 10 20 50)'
                    ;;
                show)
                    _arguments '1:run_id:'
                    ;;
            esac
            ;;
    esac
}

_skill_ralph() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '1: :->ralph_command' \
        '*: :->ralph_args'

    case $state in
        ralph_command)
            local ralph_commands=(
                'init:Initialize PRD from task description'
                'status:Show current PRD execution status'
                'start:Start Ralph automation loop'
                'next-story:Get next story to execute'
                'story-status:Get status of a specific story'
                'execute-pipeline:Execute skill pipeline for a story'
                'mark-failed:Mark a story as failed'
                'cancel:Cancel current Ralph loop'
            )
            _describe -t ralph_commands 'ralph commands' ralph_commands
            ;;
        ralph_args)
            case $line[1] in
                init)
                    _arguments \
                        '-f[Use existing PRD JSON file]:prd_file:_files -g "*.json"' \
                        '--prd-file[Use existing PRD JSON file]:prd_file:_files -g "*.json"' \
                        '1:task:'
                    ;;
                status|next-story)
                    _arguments '--json[Output as JSON]'
                    ;;
                start)
                    _arguments \
                        '-n[Maximum iterations]:max_iterations:(10 50 100 200)' \
                        '--max-iterations[Maximum iterations]:max_iterations:(10 50 100 200)' \
                        '--dry-run[Show what would run]'
                    ;;
                story-status)
                    _arguments \
                        '--story-id[Story ID to check]:story_id:' \
                        '--json[Output as JSON]'
                    ;;
                execute-pipeline)
                    _arguments \
                        '--story-id[Story ID to execute]:story_id:' \
                        '--steps[Comma-separated steps]:steps:(plan,implement plan,implement,review plan,implement,review,verify)'
                    ;;
                mark-failed)
                    _arguments \
                        '--story-id[Story ID to mark]:story_id:' \
                        '--error[Error message]:error:'
                    ;;
            esac
            ;;
    esac
}

_skill_run() {
    _arguments \
        '1:skill_name:(plan implement ui review verify)' \
        '2:task:' \
        '-f[Plan file input]:plan_file:_files -g "*.md"' \
        '--plan-file[Plan file input]:plan_file:_files -g "*.md"' \
        '--dry-run[Show what would run]' \
        '--notebook[NotebookLM notebook ID]:notebook_id:' \
        '--no-knowledge[Disable knowledge queries]'
}

_skill_common_options() {
    _arguments \
        '1:task:' \
        '-f[Plan file]:plan_file:_files -g "*.md"' \
        '--plan-file[Plan file]:plan_file:_files -g "*.md"' \
        '-i[Interactively select plan]' \
        '--interactive[Interactively select plan]' \
        '--dry-run[Show what would run]' \
        '--notebook[NotebookLM notebook ID]:notebook_id:' \
        '--no-knowledge[Disable knowledge queries]'
}

_skill_names() {
    local skills=(plan implement ui review verify)
    _describe -t skills 'skill names' skills
}

_skill "$@"
