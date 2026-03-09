---
Description: Remove excessive and unnecessary comments from code
argument-hint: [file_or_directory]
---

Remove excessive comments from the specified file(s) while preserving meaningful ones.

## Target

The target can be specified as an argument: `$ARGUMENTS`

- If a file path is provided, process that file
- If a directory is provided, process all code files in that directory
- If empty, ask the user what files to process

## What to Remove

1. **Obvious/redundant comments** that restate what the code does
   ```javascript
   // Bad - remove these:
   i++; // increment i
   return user; // return the user
   const name = user.name; // get the user's name
   ```

2. **Excessive JSDoc/docstrings** that just restate the function signature
   ```typescript
   // Bad - remove or simplify:
   /**
    * Gets the user by ID
    * @param id - The ID of the user
    * @returns The user
    */
   function getUserById(id: string): User { ... }

   // Good - keep concise if needed:
   /** Fetches user from database, returns null if not found */
   function getUserById(id: string): User | null { ... }
   ```

3. **Commented-out code** unless it has an explanatory note about why it's kept

4. **TODO/FIXME comments** that are stale or vague
   - Remove: `// TODO: fix this`
   - Keep: `// TODO(ticket-123): Handle rate limiting after API upgrade`

5. **Section dividers** that add no value
   ```javascript
   // Remove these:
   // =====================================
   // HELPER FUNCTIONS
   // =====================================
   ```

6. **Change history comments** (use git instead)
   ```javascript
   // Remove:
   // Modified by John on 2024-01-15
   // Added null check - Jane 2024-02-01
   ```

## What to Keep

- Comments explaining **why** (business logic, edge cases, workarounds)
- Comments explaining non-obvious algorithms or complex logic
- License headers and copyright notices
- API documentation for public interfaces
- Warning comments about gotchas or important constraints
- Links to relevant issues, docs, or specifications

## Process

1. Read the target file(s)
2. Identify comments that fall into the "remove" categories
3. Preserve comments that explain *why* or document important context
4. Make targeted edits to remove the noise
5. Ensure the code still compiles/runs (no accidental removals)

## Output

Provide a brief summary of what was removed, organized by file if multiple files were processed.

## Usage Examples

- `/remove-comments src/utils.ts` - Clean comments in a specific file
- `/remove-comments src/` - Clean comments in all files in src/
- `/remove-comments` - Will ask which files to process
