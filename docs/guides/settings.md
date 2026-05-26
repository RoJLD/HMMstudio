# Settings

The studio exposes a single `/settings` page (and a matching
`/api/settings` REST endpoint) for user-editable configuration. Today
there is exactly **one** setting: `warehouse_path`. The page exists so
that future settings have a natural home — but the current minimum
surface is deliberate.

## What's there today

| Setting | Type | Effect |
|---|---|---|
| `warehouse_path` | string (path) or null | Overrides the warehouse directory the studio scans. See the [Data warehouse guide](data-warehouse.md). |

That's it. A second setting will be added the day a user has a real need
for it. Until then, keeping the surface tiny keeps the UI and the data
model honest.

## Precedence model

`warehouse_path` can come from three places. The resolver picks the
first non-empty one:

1. **Database override** — set via the `/settings` page or
   `PUT /api/settings`.
2. **Environment variable** — `HMM_STUDIO_WAREHOUSE_PATH`.
3. **Unset** — the warehouse tab shows an empty state and prompts
   you to configure a path.

`GET /api/settings` surfaces all three layers at once so you can tell
which one is winning:

```json
{
  "warehouse_path": "C:/Users/rdenis/Datasets/hmm",
  "warehouse_path_source": "db",
  "warehouse_path_env": "C:/Users/rdenis/Datasets/hmm_old",
  "updated_at": "2026-05-22T15:30:00+00:00"
}
```

In this example the DB override is winning (`source: "db"`); the env
var would otherwise have pointed at the older location.

## REST API

### Read current settings

```bash
curl http://localhost:8000/api/settings
```

Returns a `SettingsResponse` with the four fields shown above.

### Update settings

```bash
curl -X PUT http://localhost:8000/api/settings \
    -H "Content-Type: application/json" \
    -d '{"warehouse_path": "C:/Users/rdenis/Datasets/hmm"}'
```

Server-side validation rejects the call if:

- The path isn't a valid filesystem path (`400`).
- The path does not exist (`400`).
- The path exists but is not a directory (`400`).

### Clear the override

Pass an empty string or `null` for `warehouse_path` — the DB row is set
to `NULL` and the resolver falls back to the env var:

```bash
curl -X PUT http://localhost:8000/api/settings \
    -H "Content-Type: application/json" \
    -d '{"warehouse_path": ""}'
```

## Updates take effect immediately

There is **no server restart needed** when settings change. The studio
keeps a small in-process cache for the warehouse scan (5-second TTL),
and the cache is explicitly invalidated by `PUT /api/settings`. The
very next `GET /api/warehouse` call re-scans the new directory.

## Pourquoi un singleton et pas un key-value bag ?

The DB schema is:

```python
class SettingsRow(SQLModel, table=True):
    id: str = Field(default="global", primary_key=True)
    warehouse_path: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)
```

A single row with `id="global"`, one column per setting. **Not** a
`(key, value)` table. Three reasons:

- **Types stay explicit.** A `warehouse_path: str | None` is checked by
  the ORM and the pydantic schema. A `Setting(key, value: str)` bag
  pushes type juggling to every call site.
- **Migrations are clear.** Adding a setting = adding a column with a
  default. Removing one = a column drop. The bag pattern hides the
  schema in your data.
- **It forces the conversation.** Each new setting requires a column,
  which requires a PR with reviewer attention. That's the right
  friction level for a config surface that should grow slowly.

When (if) we end up with a dozen settings and the columns become
unwieldy, we can revisit. We have explicitly chosen **not** to design
that abstraction in advance.

## Voir aussi

- [Data warehouse guide](data-warehouse.md) — the only consumer of
  `warehouse_path` today.
- [ADR-0010](../decisions/0010-data-warehouse-scope.md) — the same
  anti-scope-creep ethos applied to the warehouse itself.
