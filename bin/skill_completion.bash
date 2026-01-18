#!/usr/bin/env bash
# Bash completion script for Delta SkillPack CLI
# Usage: source bin/skill_completion.bash
# Or add to ~/.bashrc: source /path/to/delta-skillpack/bin/skill_completion.bash

_skill_completion() {
    local cur prev words cword
    _init_completion || return

    local commands="doctor list hello plan implement ui run pipeline history show ralph"
    local ralph_commands="init status start next-story story-status execute-pipeline mark-failed cancel"

    case "${prev}" in
        skill)
            COMPREPLY=($(compgen -W "${commands}" -- "${cur}"))
            return 0
            ;;
        ralph)
            COMPREPLY=($(compgen -W "${ralph_commands}" -- "${cur}"))
            return 0
            ;;
        run)
            # Suggest available skill names
            local skills="plan implement ui review verify"
            COMPREPLY=($(compgen -W "${skills}" -- "${cur}"))
            return 0
            ;;
        -f|--plan-file)
            # Complete file paths for plan files
            COMPREPLY=($(compgen -f -- "${cur}"))
            return 0
            ;;
        -n|--limit|--max-iterations)
            # Suggest common numeric values
            COMPREPLY=($(compgen -W "5 10 20 50 100" -- "${cur}"))
            return 0
            ;;
        --story-id)
            # Could be enhanced to list actual story IDs
            return 0
            ;;
        --steps)
            # Suggest common step combinations
            COMPREPLY=($(compgen -W "plan,implement plan,implement,review plan,implement,review,verify" -- "${cur}"))
            return 0
            ;;
    esac

    # Handle options
    if [[ "${cur}" == -* ]]; then
        local opts=""
        case "${words[1]}" in
            plan|implement|ui|run)
                opts="-f --plan-file --dry-run --notebook --no-knowledge"
                ;;
            pipeline)
                opts="--dry-run"
                ;;
            history)
                opts="-n --limit"
                ;;
            ralph)
                case "${words[2]}" in
                    init)
                        opts="-f --prd-file"
                        ;;
                    status|next-story|story-status)
                        opts="--json"
                        ;;
                    start)
                        opts="-n --max-iterations --dry-run"
                        ;;
                    execute-pipeline)
                        opts="--story-id --steps"
                        ;;
                    mark-failed)
                        opts="--story-id --error"
                        ;;
                esac
                ;;
        esac
        COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
        return 0
    fi
}

complete -F _skill_completion skill
