OpenCode Improvement State
This directory tracks the AI-driven improvement workflow for this repository.

Files
STATE.md - Current analysis context and recent changes
IMPROVEMENTS.md - Log of all completed improvements
PLAN.md - High-level roadmap and goals
metrics/ - Performance and quality metrics over time
How It Works
OpenCode runs on develop branch
Analyzes current codebase state
Checks GitHub issues for human input
Determines next improvement (autonomous)
Implements and tests
Updates these state files
Commits to develop
Creates PR to main (auto-merges on success)
Human Input
Create GitHub issues with labels:

opencode-priority - Must do next
opencode-question - Needs human decision
opencode-bug - Issue found by AI
