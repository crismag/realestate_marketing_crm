"""Spreadsheet (CSV) import of contacts.

Two steps so nothing surprising lands in the CRM:
1. ``parse_upload`` reads the file, recognises the columns, validates every row with the same rules as the
   capture form and marks possible duplicates (existing contacts or earlier rows in the same file).
2. ``run_import`` creates the rows the person kept, each through ``capture_contact`` so responsibility,
   history and audit are the same as a manual capture.

Responsibility follows ADR-001/002: imported contacts go to the person importing or to a shared pool.
Nobody can import contacts straight into a colleague's name; agents import their own book, or the office
imports into a pool and agents claim.
"""
from __future__ import annotations

import csv
import io

from django.db import transaction

from crm.core import clock
from crm.core.errors import ConflictError, DomainError
from crm.core.services import audit

from . import services
from .forms import ContactFieldsForm
from .models import LIFECYCLES, ContactImport, Source

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000

# Header aliases (compared lower-case with spaces, dashes and underscores removed).
ALIASES = {
    "display_name": ["name", "fullname", "displayname", "clientname", "customername", "contactname", "customer", "client"],
    "first_name": ["firstname", "givenname", "first"],
    "last_name": ["lastname", "surname", "familyname", "last"],
    "email": ["email", "emailaddress", "e-mail", "mail"],
    "phone": ["phone", "mobile", "mobilenumber", "phonenumber", "contactnumber", "cellphone", "cell", "telephone", "tel"],
    "source": ["source", "leadsource", "acquisitionsource", "channel"],
    "source_detail": ["sourcedetail", "campaign", "event", "referredby", "referral"],
    "interests": ["interests", "requirements", "lookingfor", "propertyinterest", "budget", "interest"],
    "notes": ["notes", "note", "remarks", "comments", "comment"],
    "lifecycle": ["lifecycle", "stage", "status", "type", "leadstatus"],
}
TEMPLATE_HEADERS = ["Name", "Email", "Phone", "Source", "Source detail", "Interests", "Notes", "Lifecycle"]


def _key(header: str) -> str:
    return "".join(ch for ch in header.lower() if ch.isalnum())


def recognise(headers: list[str]) -> dict[str, str]:
    """Map each recognised header to a field; unknown headers are ignored (and shown as ignored)."""
    lookup = {_key(alias): field for field, aliases in ALIASES.items() for alias in aliases}
    mapping, used = {}, set()
    for h in headers:
        field = lookup.get(_key(h))
        if field and field not in used:
            mapping[h] = field
            used.add(field)
    return mapping


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _strip_formula_guard(value: str) -> str:
    # Our own CSV export prefixes risky cells with an apostrophe; undo that on the way back in.
    if len(value) > 1 and value[0] == "'" and value[1] in "=+-@":
        return value[1:]
    return value


def _lifecycle_lookup(policy: dict) -> dict[str, str]:
    lookup = {}
    for code, label in LIFECYCLES:
        lookup[_key(code)] = code
        lookup[_key(label)] = code
        lookup[_key(policy["lifecycle_labels"].get(code, label))] = code
    return lookup


def _source_lookup() -> dict[str, Source]:
    lookup = {}
    for s in Source.objects.filter(active=True):
        lookup[_key(s.code)] = s
        lookup[_key(s.label)] = s
    return lookup


def parse_upload(*, actor, upload, destination: str, pool=None, default_source=None, policy: dict) -> ContactImport:
    if destination not in ("me", "pool"):
        raise DomainError("Choose who is responsible for the imported contacts.", code="invalid_destination")
    if destination == "pool" and (pool is None or not pool.active):
        raise DomainError("Choose an active pool.", code="invalid_destination")
    if upload.size > MAX_BYTES:
        raise DomainError("The file is larger than 2 MB. Split it into smaller files.", code="too_large")
    filename = upload.name or "upload.csv"
    if filename.lower().endswith((".xlsx", ".xls", ".numbers", ".ods")):
        raise DomainError("Save the spreadsheet as CSV (File → Save as → CSV UTF-8) and upload that file.",
                          code="not_csv")
    text = _decode(upload.read(MAX_BYTES + 1))
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    try:
        headers = [h.strip() for h in next(reader)]
    except StopIteration:
        raise DomainError("The file is empty.", code="empty") from None
    mapping = recognise(headers)
    fields = set(mapping.values())
    if "display_name" not in fields and not {"first_name", "last_name"} & fields:
        raise DomainError("No name column found. Add a column called Name (or First name and Last name).",
                          code="no_name_column")

    sources = _source_lookup()
    lifecycles = _lifecycle_lookup(policy)
    extended = services.extended_matching_enabled()
    rows, seen_email, seen_phone = [], {}, {}
    for line, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        if len(rows) >= MAX_ROWS:
            raise DomainError(f"The file has more than {MAX_ROWS} rows. Split it into smaller files.", code="too_many_rows")
        cells = {mapping[h]: _strip_formula_guard(values[i].strip())
                 for i, h in enumerate(headers) if h in mapping and i < len(values)}
        name = cells.get("display_name") or " ".join(p for p in (cells.get("first_name"), cells.get("last_name")) if p)
        data = {"display_name": name, "email": cells.get("email", ""), "phone": cells.get("phone", ""),
                "source_detail": cells.get("source_detail", ""), "interests": cells.get("interests", ""),
                "notes": cells.get("notes", "")}
        errors = []
        source = default_source
        if cells.get("source"):
            match = sources.get(_key(cells["source"]))
            if match is not None:
                source = match
            else:
                data["source_detail"] = (data["source_detail"] + f" (source: {cells['source']})").strip()
        lifecycle = "lead"
        if cells.get("lifecycle"):
            lifecycle = lifecycles.get(_key(cells["lifecycle"]), "")
            if not lifecycle:
                errors.append(f"Unknown lifecycle '{cells['lifecycle']}'.")
        form = ContactFieldsForm({**data, "source": source.pk if source else ""})
        if not form.is_valid():
            for field, messages in form.errors.items():
                label = "Row" if field == "__all__" else form.fields[field].label or field.replace("_", " ").capitalize()
                errors.extend(f"{label}: {m}" for m in messages)
        duplicates = []
        if not errors:
            duplicates = [{"id": c.pk, "name": c.display_name}
                          for c in services.duplicate_candidates(email=data["email"], phone=data["phone"], name=name,
                                                                 extended=extended)[:3]]
            email_key = services.normalize_email(data["email"])
            phone_key = services.normalize_phone(data["phone"])
            earlier = seen_email.get(email_key) if email_key else None
            earlier = earlier or (seen_phone.get(phone_key) if phone_key else None)
            if earlier:
                duplicates.append({"line": earlier, "name": f"row {earlier} of this file"})
            if email_key:
                seen_email.setdefault(email_key, line)
            if phone_key:
                seen_phone.setdefault(phone_key, line)
        rows.append({"line": line, "data": data, "source_id": source.pk if source else None, "lifecycle": lifecycle,
                     "errors": errors, "duplicates": duplicates,
                     "status": "error" if errors else ("duplicate" if duplicates else "ready")})
    if not rows:
        raise DomainError("The file has headers but no rows.", code="empty")
    with transaction.atomic():
        imp = ContactImport.objects.create(created_by=actor, filename=filename[:200], destination=destination,
                                           pool=pool if destination == "pool" else None, default_source=default_source,
                                           columns=mapping, rows=rows)
        audit("import.previewed", imp, f"Previewed import of {len(rows)} row(s) from {imp.filename}", actor=actor)
    return imp


def counts(imp: ContactImport) -> dict:
    result = {"ready": 0, "duplicate": 0, "error": 0, "created": 0, "skipped": 0}
    for row in imp.rows:
        result[row["status"]] = result.get(row["status"], 0) + 1
    result["total"] = len(imp.rows)
    return result


def run_import(imp: ContactImport, *, actor, include_duplicates: bool) -> ContactImport:
    """Create the contacts. Runs once: the preview -> running flip is conditional."""
    if imp.created_by_id != actor.pk:
        raise DomainError("Only the person who uploaded the file can run this import.", code="not_owner")
    if not ContactImport.objects.filter(pk=imp.pk, status="preview").update(status="running"):
        raise ConflictError("This import has already run or was cancelled.", code="import_not_pending")
    imp.refresh_from_db()
    sources = {s.pk: s for s in Source.objects.all()}
    created = skipped = 0
    for row in imp.rows:
        if row["status"] == "error" or (row["status"] == "duplicate" and not include_duplicates):
            row["status"] = "skipped" if row["status"] == "duplicate" else row["status"]
            skipped += row["status"] == "skipped"
            continue
        data = {**row["data"], "source": sources.get(row["source_id"])}
        try:
            result = services.capture_contact(actor=actor, data=data, destination=imp.destination, pool=imp.pool)
            if row["lifecycle"] != "lead":
                services.set_lifecycle(result.contact, actor=actor, lifecycle=row["lifecycle"], disposition="active",
                                       reason=f"Imported from {imp.filename}", expected_version=result.contact.version)
        except DomainError as exc:
            row["status"], row["errors"] = "error", [exc.message]
            continue
        row["status"], row["contact_id"] = "created", result.contact.pk
        created += 1
    imp.status, imp.finished_at = "done", clock.now()
    imp.summary = {"created": created, "skipped": skipped, "errors": sum(1 for r in imp.rows if r["status"] == "error")}
    with transaction.atomic():
        imp.save(update_fields=["status", "finished_at", "summary", "rows"])
        audit("import.completed", imp, f"Imported {created} contact(s) from {imp.filename}", actor=actor, data=imp.summary)
    return imp


def cancel_import(imp: ContactImport, *, actor) -> None:
    if imp.created_by_id != actor.pk:
        raise DomainError("Only the person who uploaded the file can cancel this import.", code="not_owner")
    if not ContactImport.objects.filter(pk=imp.pk, status="preview").update(status="cancelled"):
        raise ConflictError("This import has already run or was cancelled.", code="import_not_pending")
    audit("import.cancelled", imp, f"Cancelled import of {imp.filename}", actor=actor)


def template_csv() -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerow(["Maria Santos", "maria@example.test", "+63 917 555 0199", "Referral", "Referred by a past client",
                     "3BR condo in Makati, budget 15M", "Prefers calls after 6pm", "Lead"])
    return out.getvalue()
