# implementation rule
- each file no more than 1000 lines


# code implementation rule
- we are in developing stage, don't worry about backward compatibility, just modify code file, migration script, infrastructure file directly. Don't create new _V2 or _enhanced version.
- we need to enforce strict type in both frontend and backend function input and output, Dict[str, Any] or Any is not allowed
- each function should be self-explain with a docstring explain its function, input and output type
- implementation and unittest file should be implemented at the same time (try find existing test file and modify it first don't always create new test file)

# Developer environment
- backend: use uv in backend/.venv
- frontend: use pnpm in frontend 
- supabase: migration in project root folder