---
paths:
  - "**/*.{js,jsx,ts,tsx}"
---

# Naming in JavaScript and TypeScript

This adds to the general naming rules and says how JavaScript and TypeScript spell them.

## Spelling

- `camelCase` for functions, methods and variables: `findCustomer`, `isPaid`.
- `PascalCase` for classes, types and components: `OrdersRepository`.
- `UPPER_SNAKE_CASE` for constants at module level: `MAX_IMAGE_SIDE_PX`.

## Private names

A private class member is written with `#`: `#formatMoney`. A function private to a module is simply
not exported and takes no prefix.

## React

These apply only in a project that uses React, and each is an exception to the general rules:

- A component is a noun, not a verb: `OrderSummary`.
- `handle…` names an event handler and `on…` the prop that receives it: `handleSubmit`, `onSubmit`.
- `use…` is a hook, as React requires: `useOrders`. A function that is not a hook does not start
  with `use`.
