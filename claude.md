# implementation rule
- each file no more than 1000 lines
- if any feature you thinks is helpful just add and merge it to $projectroot/TODO.md(don't create duplicate items)


# code implementation rule
- we are in developing stage, don't worry about backward compatibility, just modify code file, migration script, infrastructure file directly. Don't create new _V2 or _enhanced version.
- we need to enforce strict type in both frontend and backend function input and output, Dict[str, Any] or Any types are not allowed
- each function should be self-explain with a docstring explain its function, input and output type
- each function file should have a short description in the beginning explain what this file do
- source code implementation and unittest file should be implemented at the same time (try find existing test file and modify it first don't always create new test file)
- function doc string and file description should be updated at the same time
- each main folder can have a readme.md file


# Developer environment
- backend: use uv in backend/.venv
- frontend: use pnpm in frontend 
- supabase: migration in project root folder