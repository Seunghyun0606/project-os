# Versioning

Project OS separates three versions.

## Package version

The version of the `projectctl` Python package.

Sources:
- `pyproject.toml`
- `VERSION`
- `projectctl.__version__`

## Scaffold version

The version of the consumer scaffold generated for new projects.

Stored in `.project-os/manifest.yaml` as `project_os.scaffold_version`.

A scaffold release may change defaults or bootstrap files without changing the underlying schema.

## Schema version

The version of the data contract used by `.project-os` state/task files.

Stored in `.project-os/manifest.yaml` as `project_os.schema_version`.

Breaking file-format changes require a schema-version bump and an explicit migration.

## Upgrade rule

Never upgrade an existing consumer project by copying the latest scaffold over it.

Future `projectctl upgrade` behavior must:

1. Read package, scaffold and schema versions.
2. Detect required migrations.
3. Require a clean/recoverable Git state or explicit override.
4. Apply only known migrations in order.
5. Run `projectctl doctor`.
6. Refuse unknown or lossy migrations without explicit approval.

## Compatibility

The manifest contains `package_compatibility` so a consumer repository can declare which projectctl range is safe to use.

## Release checklist

- Update VERSION.
- Update pyproject version.
- Update projectctl.__version__.
- Update scaffold version when consumer template changes.
- Update schema version only for schema-breaking changes.
- Update CHANGELOG.
- Run tests.
- Generate a fresh scaffold and run doctor against it.
