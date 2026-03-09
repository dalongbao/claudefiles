---
Description: Remove AI code slop and clean up code
argument-hint: [base_branch]
---

Clean up code and remove all AI-generated slop from **all files changed in the current branch**.

## Step 1: Determine What to Clean

The target branch to compare against can be specified as an argument: `$ARGUMENTS`

If no argument is provided or it's empty, auto-detect the base branch:
1. Run `git remote show origin | grep 'HEAD branch'` to find the default branch
2. If that fails, check if `origin/main` exists, then `origin/master`
3. Use whichever exists (prefer `main` over `master`)

Then get the list of changed files:
```bash
git fetch origin
git diff --name-only $BASE_BRANCH...HEAD
```

These are the files to clean up - all files modified in this branch compared to the base.

## What to Clean Up

1. **Extra comments** that a human wouldn't add or that are inconsistent with the rest of the file
   - Remove obvious/redundant comments like `// increment counter` above `i++`
   - Remove excessive JSDoc or docstrings that just restate the function name
   - Keep comments that explain *why*, remove those that explain *what*

2. **Extra defensive checks** or try/catch blocks that are abnormal for that area of the codebase
   - Remove unnecessary null checks for values that can't be null
   - Remove redundant try/catch blocks especially if called by trusted/validated codepaths
   - Keep error handling at system boundaries (user input, external APIs)

3. **Casts to `any`** (or equivalent) to get around type issues
   - Fix the underlying type issue instead of casting
   - If a cast is truly necessary, add a brief comment explaining why

4. **Variables used only once** right after declaration - inline the right-hand side
   ```typescript
   // Before (slop)
   const userId = user.id;
   await saveUser(userId);

   // After (clean)
   await saveUser(user.id);
   ```

5. **Over-abstracted helpers** for one-time operations
   - Inline small helper functions that are only called once
   - Remove unnecessary wrapper functions

6. **Style inconsistencies** with the rest of the file
   - Match existing naming conventions
   - Match existing formatting patterns
   - Match existing import organization

7. **Redundant code patterns**
   - Remove `else` after `return`/`throw`/`continue`
   - Simplify boolean expressions (`if (x === true)` → `if (x)`)
   - Remove unnecessary async/await on already-resolved values

## Process

1. Determine base branch (from `$ARGUMENTS` or auto-detect main/master)
2. Get the list of files changed in the branch: `git diff --name-only $BASE_BRANCH...HEAD`
3. For each changed file:
   - Read the file
   - Check the diff for that file to see what was added/changed: `git diff $BASE_BRANCH...HEAD -- <file>`
   - Focus cleanup efforts on the changed sections
   - Analyze surrounding codebase style for context
   - Identify instances of AI slop in the changed code
   - Make targeted edits to clean up
4. Preserve the original functionality - only remove noise, don't change behavior

## Output

Report at the end with only a 1-3 sentence summary of what you changed.

## Usage Examples

- `/cleanup` - Clean up all files changed in branch vs main/master
- `/cleanup develop` - Clean up files changed vs `origin/develop`
