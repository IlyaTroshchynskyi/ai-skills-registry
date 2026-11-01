---
paths:
  - "**/*.py"
---

# Naming in Python

This adds to the general naming rules and says how Python spells them.

## Spelling

- `snake_case` for functions, methods, variables and modules: `find_customer`.
- `PascalCase` for classes: `OrdersRepository`.
- `UPPER_SNAKE_CASE` for constants: `MAX_IMAGE_SIDE_PX`.

## Private names

A leading underscore marks a name as private to its module or class, and a private function keeps
it: `_format_money`. It is not a type or role prefix, and the name after it follows the same rules:
`_money` -> `_format_money`.

## Verbs

- `open_…` an async context manager that owns its client - `open_database_session`
