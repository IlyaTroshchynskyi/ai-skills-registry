# Naming

These rules hold in any language. The examples are in snake_case: spell a name the way the language
in use does, including its case and how it marks a private name.

An established convention of the project wins over this file. Follow the names already in the code
rather than introduce a second style beside them.

## Functions get verbs, values get nouns

A function's name starts with a verb - a one-line private helper, a method and a test helper
included:

- `money(amount)` -> `format_money(amount)`
- `invoice.total(tax_rate)` -> `invoice.compute_total(tax_rate)`
- `permissions(user)` -> `build_permission_map(user)`

A bare noun is reserved for a value: `reason = find_refund_reason(order, policy)`. A property reads
like a value, so it is named like one (`invoice.total_due`, `invoice.label`), and so is a constant
(`ONE_REFUND_PER_ORDER_RULE`, not `ONE_AT_A_TIME`; `UNPAID_ORDER_NOTICE`, not `ORDER_NOT_PAID`). A
value is not named by a participle either: `extracted_fields`, not `extracted`; `read_error`, not
`unreadable`.

## The verb says what the function actually does

`get_` is only for handing back something that already exists: a field, or an object built once and
cached (`get_settings`, `get_connection_pool`). Anything that looks something up or transforms it
takes the verb for that shape of work:

- `find_…`      looks something up by a name or a key and may find nothing - `find_customer`,
  `find_orders_by_email`
- `list_…`      every row of one kind - `list_invoices`, `list_open_tickets`
- `build_…`     assembles a structure or a prompt - `build_report`, `build_search_query`
- `compute_…`   numeric result - `compute_total`
- `check_…`     holds a fact against a rule and returns the verdict - `check_password_strength`,
  `check_order_limit`
- `pick_…`      chooses one out of several - `pick_cheapest_carrier`
- `parse_…`     unstructured input -> typed shape, with nothing but the input - `parse_csv_rows`
- `read_…`      bytes taken in from outside and handed on in a typed shape - `read_config_file`
- `normalize_…` one spelling out of many - `normalize_email`
- `format_…`    value -> display string - `format_money`, `format_date`

`handle_password` is wrong where `check_password_strength` is right: the verb must name the
operation, not gesture at it.

## The noun names the domain type

Qualify with the type the function works on: `build_order_summary`, not `build_summary`;
`pick_cheapest_carrier`, not `pick_cheapest`; `find_refund_reason`, not `reason_for`;
`check_order_limit`, not `check_limit`.

## Names reveal intent

A name says why the thing exists, what it does and how it is used. If it needs a comment or a look
into the body to answer that, rename it.

- `peak = 0` -> `peak_concurrency = 0`
- `sleep(0.05)` -> `sleep(RETRY_DELAY_SECONDS)`
- `if order.paid_by != email and order.status == 'paid'` -> `if is_paid_by_someone_else(order, email)`
- a nested expression that needs explaining gets a named intermediate value instead:
  `overdue_invoices = …`

## Booleans read as a yes/no statement

- Variables, fields, arguments and predicate functions start with `is_`, `has_`, `can_` or
  `should_`: `order.is_paid`, `condition.is_met`, `is_admin`.
- Positive form: `is_visible`, not `is_not_hidden` - a negative name turns every check into a double
  negative.
- A boolean argument hides a second function. `build_pdf(encrypted=True)` says nothing where it is
  called; write `build_encrypted_pdf()`.

## No disinformation, no noise

- A name never claims a shape the value does not have: `customer_list` is a list, not a dict;
  `prices_by_product` is a lookup, not one product's prices.
- Words that distinguish nothing are not names: `data`, `info`, `item`, `obj`, `result`, `value`,
  `tmp`, `stub`. If `order` and `order_data` both exist, the reader cannot tell which one to pass. A
  word like that is fine once something qualifies it: `field_value`, `stored_orders`.
- No numbered series: `price1`, `price2` -> `old_price`, `new_price`.
- Names do not look alike: no `l` beside `1`, no `O` beside `0`, no two long names that differ by one
  word in the middle.

## Whole, searchable words

- Write the word out: `index`, `response`, `document`, `error`, `task_group`, `characters` - not
  `idx`, `resp`, `doc`, `exc`, `tg`, `chars`. A name must be pronounceable in review and findable by
  search.
- The names of things stay as the world spells them: `pdf`, `png`, `id`, `url`, `sql`. A unit closes
  a constant in the same way: `REQUEST_TIMEOUT_SECONDS`, `MAX_IMAGE_SIDE_PX`.
- Length follows scope. A single letter is acceptable only as a counter in a loop of a few lines; a
  variable in a comprehension or a callback is the singular of its collection -
  `[customer.name for customer in customers]`.
- No type or role encoded in the name: `answer`, not `answer_str`; `users`, not `users_list`;
  `Notifier`, not `INotifier` or `NotifierProtocol`.

## One word per concept, one concept per word

- Before adding a verb, check the list above and the verbs already in the project for one that
  already means it. Two words for one operation - `fetch_…` beside `get_…`, `make_…` beside
  `build_…` - make the reader look for a difference that is not there.
- A verb keeps one meaning everywhere: if `add_…` appends to a collection, do not also use it to sum
  numbers.
- Plain over clever: `delete_expired_sessions`, not `sweep_sessions`.

## The name tells everything the function does

- A side effect belongs in the name: a getter that creates the row when it is missing is
  `get_or_create_session`, not `get_session`.
- If the honest name needs `and`, the function does two things - split it.
- A function that only answers a question never changes state: `is_paid` and `check_order_limit` do
  not write.
- The name stays at the caller's level and says what, not how: `cancel_subscription`, not
  `update_subscription_status_attribute`.

## Types and classes get nouns

A class, protocol or type alias is a noun phrase: `OrdersRepository`, `InvoiceLine`, `Verdict`.
`Manager`, `Processor`, `Helper` and `Utils` name no responsibility - say what the type holds or
does instead.

## Just enough context

- Do not repeat what the owner already says: `order.status`, not `order.order_status`.
- When a name alone is ambiguous, let its owner give the context: `address.state`, not a bare `state`.
- Use the word the business uses for a domain thing and the pattern name for a technical one:
  `order`, `invoice`, `customer`; `…Repository`, `…Service`, `…Factory`.
