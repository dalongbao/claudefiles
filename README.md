# claudefiles
> my spinnertexts are custom undead unluck ones i wrote myself for every negator in the series. you can write your own, just look at the [claude code docs](https://code.claude.com/docs) 

My Claude Code configuration — custom commands, permissions, hooks, and settings.

## Credits

Several commands in `commands/` are from [tokenbender/agent-guides](https://github.com/tokenbender/agent-guides):
- `analyze-function.md`
- `crud-claude-commands.md`
- `multi-mind.md`
- `page.md`
- `search-prompts.md`

## raw note stream when figuring claude out
> note that since then, anthropic pushed a bunch more changes to claude code that made some of these easier. btw. 
- always use opus subagents
- use plan mode -> generate a plan -> execute step by step
- use claude.md file 
	- prefix prompt with #, will save to the claude.md
	- claude.md file in each subdir to instruct tests/backends/services/etc
	- documents bash commands, files/utility functions, code guidelines, test instructions, naming etiquette, env setup, warnings to the project, etc
	- example setup:
```
# Bash commands
- npm run build: Build the project
- npm run typecheck: Run the typechecker

# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow
- Be sure to typecheck when you’re done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance 
```
- git worktrees for multiple claude instances on the same codebase without conflicts
- multiple subagents -> ask claude to use subagents
- project specific slash commands -> .claude/commands (agent-guides)
- `think`, `think harder`, `ultrathink`
- git commit using claude
- document everything in intermediate markdowns
- --resume preserves context
- MCP servers
- `bunx ccusage blocks --live` for usage limits
- verification mechanism (tests, etc etc)
- lots of flags you can use to set claude behaviour - e.g. 

``` 
function ccv() {
  local env_vars=(
    "ENABLE_BACKGROUND_TASKS=true"
    "FORCE_AUTO_BACKGROUND_TASKS=true"
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true"
    "CLAUDE_CODE_ENABLE_UNIFIED_READ_TOOL=true"
  )
  
  local claude_args=()
  
  if [[ "$1" == "-y" ]]; then
    claude_args+=("--dangerously-skip-permissions")
  elif [[ "$1" == "-r" ]]; then
    claude_args+=("--resume")
  elif [[ "$1" == "-ry" ]] || [[ "$1" == "-yr" ]]; then
    claude_args+=("--resume" "--dangerously-skip-permissions")
  fi
  
  env "${env_vars[@]}" claude "${claude_args[@]}"
}
```
- write commands in `.claude/commands` for repeated workflows - e.g. `/fixissue 392`
```
Please analyze and fix the GitHub issue: $ARGUMENTS.

Follow these steps:

1. Use `gh issue view` to get the issue details
2. Understand the problem described in the issue
3. Search the codebase for relevant files
4. Implement the necessary changes to fix the issue
5. Write and run tests to verify the fix
6. Ensure code passes linting and type checking
7. Create a descriptive commit message
8. Push and create a PR

Remember to use the GitHub CLI (`gh`) for all GitHub-related tasks.
```
- verbose instructions, be specific
- paste urls for claude to read
- `/clear` to clear context window 
- checklist and scratchpad maxx -> markdown
- multi agent reasoning
- multiple folders -> multiple git checkouts 
	- claude each one
	- cycle 
	- git worktrees allow that to happen more lightweight-ly
- `-p` is headless mode, allows claude to crawl through bigger chunks of data
	- e.g. `claude -p “migrate foo.py from React to Vue. When you are done, you MUST return the string OK if you succeeded, or FAIL if the task failed.” --allowedTools Edit Bash(git commit:*)`
	- can pipe tests into this workflow
- inline slash commands
	- /commit-push-pr
	- /permissions to allow common bash commands instead of --dangerously-skip-permissions
- 

# sources
https://www.reddit.com/r/ClaudeAI/comments/1lkfz1h/how_i_use_claude_code/
https://github.com/modelcontextprotocol/servers
https://github.com/tokenbender/agent-guides
https://www.anthropic.com/engineering/claude-code-best-practices
https://code.claude.com/docs/en/terminal-config#iterm-2-system-notifications
https://sankalp.bearblog.dev/my-experience-with-claude-code-20-and-how-to-get-better-at-using-coding-agents/

# commands i'd like
- ls
- grep
- find
- python3/python
- docker
- cd

# global settings
general case bash functions: 
- ls
- grep
- which
- find

# local settings
- build commands
- docker permissions
- 

# claude.md

# subagents
example subagent: 

`.claude/agents/agent-name.md` or `/agents`
```
<!--
name: 'Agent Prompt: Explore'
description: System prompt for the Explore subagent
ccVersion: 2.0.56
variables:
  - GLOB_TOOL_NAME
  - GREP_TOOL_NAME
  - READ_TOOL_NAME
  - BASH_TOOL_NAME
-->
You are a file search specialist for Claude Code, Anthropic's official CLI for Claude. You excel at thoroughly navigating and exploring codebases.

=== CRITICAL: READ-ONLY MODE - NO FILE MODIFICATIONS ===
This is a READ-ONLY exploration task. You are STRICTLY PROHIBITED from:
- Creating new files (no Write, touch, or file creation of any kind)
- Modifying existing files (no Edit operations)
- Deleting files (no rm or deletion)
- Moving or copying files (no mv or cp)
- Creating temporary files anywhere, including /tmp
- Using redirect operators (>, >>, |) or heredocs to write to files
- Running ANY commands that change system state

Your role is EXCLUSIVELY to search and analyze existing code. You do NOT have access to file editing tools - attempting to edit files will fail.

Your strengths:
- Rapidly finding files using glob patterns
- Searching code and text with powerful regex patterns
- Reading and analyzing file contents

Guidelines:
- Use ${GLOB_TOOL_NAME} for broad file pattern matching
- Use ${GREP_TOOL_NAME} for searching file contents with regex
- Use ${READ_TOOL_NAME} when you know the specific file path you need to read
- Use ${BASH_TOOL_NAME} ONLY for read-only operations (ls, git status, git log, git diff, find, cat, head, tail)
- NEVER use ${BASH_TOOL_NAME} for: mkdir, touch, rm, cp, mv, git add, git commit, npm install, pip install, or any file creation/modification
- Adapt your search approach based on the thoroughness level specified by the caller
- Return file paths as absolute paths in your final response
- For clear communication, avoid using emojis
- Communicate your final report directly as a regular message - do NOT attempt to create files

NOTE: You are meant to be a fast agent that returns output as quickly as possible. In order to achieve this you must:
- Make efficient use of the tools that you have at your disposal: be smart about how you search for files and implementations
- Wherever possible you should try to spawn multiple parallel tool calls for grepping and reading files

Complete the user's search request efficiently and report your findings clearly.
```

# hooks
> They allow you to observe when a certain stage in the agent loop lifecycle starts or ends and let you run bash scripts before or after to make changes to the agent loop.
- stop
- do more
