# Permissions Required for CSV Export Button

## Context

Work package **#40** — investigate the permissions a user needs to access the
CSV export button on the invoices list page (see seed idea: "Let accountants
export the invoices list to CSV").

This document covers the permission model that should govern the feature,
identifies each required permission, and recommends how roles should be
configured.

---

## Permission Model Overview

The application uses role-based access control (RBAC). Permissions are assigned
to **roles**, and roles are assigned to **users** within a project or
organisation scope. The CSV export button must be gated on a combination of
data-access and export-specific permissions so that users can only export
records they are already authorised to view.

---

## Required Permissions

A user must hold **all** of the following permissions to see and use the CSV
export button on the invoices page.

### 1. `view_invoices`

| Attribute   | Value                                                  |
|-------------|--------------------------------------------------------|
| Scope       | Project / organisation                                 |
| Description | Grants read access to the invoices list and detail views. |
| Effect      | Without this, the invoices page itself is inaccessible — the export button is never rendered. |

There may be a granular split between `view_own_invoices` (user sees only
invoices they created or are assigned to) and `view_invoices` (user sees all
invoices in the project). The export must respect whichever variant the user
holds — it should never include rows the user cannot see on screen.

### 2. `export_work_packages` (or `export_invoices`)

| Attribute   | Value                                                  |
|-------------|--------------------------------------------------------|
| Scope       | Project / organisation                                 |
| Description | Grants the ability to trigger bulk data exports (CSV, XLS, PDF) from list views. |
| Effect      | Without this, the export button is hidden even if the user can view the invoices list. |

In OpenProject's permission model, the analogous permission is
**"Export work packages"**, which controls whether the CSV/XLS/PDF export
actions appear on the work packages list. For the invoices feature, this
translates to a dedicated `export_invoices` permission or a shared
`export_data` permission that covers all exportable list views.

**Recommendation:** Use a dedicated `export_invoices` permission rather than a
blanket `export_data` flag. This lets administrators grant accountants invoice
exports without inadvertently enabling exports from other modules (e.g., HR or
payroll).

### 3. Authentication (implicit)

The user must be authenticated. Anonymous / public users must never see the
export button, regardless of role configuration.

---

## Filter and Scope Enforcement

The CSV export must apply the **same filters and visibility rules** as the
invoices list view. Specifically:

- **Row-level filtering:** If the user holds `view_own_invoices` instead of
  `view_invoices`, the export must only include their own invoices.
- **Active filters:** If the user has applied date-range, status, or
  customer filters on the list, the export must respect them. The export
  endpoint should accept the same filter parameters as the list endpoint.
- **Project scope:** If the user's role is scoped to a specific project, the
  export must not leak invoices from other projects.

---

## Role-to-Permission Mapping (Recommended)

| Role            | `view_invoices` | `view_own_invoices` | `export_invoices` | Notes                              |
|-----------------|:---------------:|:-------------------:|:-----------------:|------------------------------------|
| Admin           | yes             | yes (implied)       | yes               | Full access                        |
| Finance Manager | yes             | yes (implied)       | yes               | Primary user of the export feature |
| Accountant      | yes             | yes (implied)       | yes               | The original requestor persona     |
| Auditor         | yes             | yes (implied)       | yes               | Read-only, but export is essential for audit trails |
| Project Member  | no              | yes                 | no                | Can view own invoices but cannot bulk-export |
| Viewer          | no              | no                  | no                | No invoice access                  |

---

## Implementation Notes

1. **Button visibility:** The UI should check `export_invoices` (or its
   equivalent) before rendering the export button. A server-side guard must
   also reject the export API call if the permission is missing — client-side
   hiding alone is insufficient.

2. **OpenProject API parallel:** In OpenProject, the `GET
   /api/v3/projects/:id/work_packages` endpoint supports a `Content-Type:
   text/csv` accept header when the user's role includes the "Export work
   packages" permission. A similar pattern (accept-header or dedicated
   `/invoices/export.csv` endpoint) should be used here.

3. **Rate limiting / abuse prevention:** Bulk exports can be expensive. Consider
   rate-limiting the export endpoint (e.g., max 5 exports per user per minute)
   independently of the permission check.

4. **Audit logging:** Every export should be logged with the user ID,
   timestamp, applied filters, and row count. This is especially important for
   finance data where audit trails are a compliance requirement.

---

## Summary

| # | Permission            | Purpose                          | Required |
|---|-----------------------|----------------------------------|----------|
| 1 | `view_invoices` (or `view_own_invoices`) | Access the invoices list page | Yes |
| 2 | `export_invoices`     | Trigger CSV/bulk export          | Yes      |
| 3 | Authenticated session | Basic access control             | Yes      |

All three must be satisfied simultaneously. The export payload must respect the
same row-level visibility and filter parameters as the list view.
