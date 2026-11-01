# No comments in code

Write code with no comments:

- no inline comments (`// ...`, `# ...`)
- no doc comments: JSDoc, TSDoc or docstrings, including on exported types, functions and interfaces
- no block comments (`/* ... */`)
- no `TODO` / `FIXME` / `NOTE` markers
- no commented-out code

One exception: a comment that explains a non-obvious constraint — a reason the code cannot show, such
as why an order is load-bearing or what an external system requires — is allowed.

Text that a tool reads is not a comment and stays: a shebang, `# noqa`, `# type: ignore`,
`// @ts-expect-error`, `// eslint-disable-next-line`, a docstring that becomes CLI help or API
documentation, a license header the project requires.

Applies to tests exactly as it applies to production code. Name variables, functions, types and
test cases so the code reads on its own; if a comment feels necessary, rename or restructure
instead.

Explanation that would have gone into a comment belongs in the reply to the user, the commit
message, or the merge request description.
