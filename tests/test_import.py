"""Spreadsheet import: preview first, validate like capture, flag duplicates, run once (product step 3)."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from crm.contacts import importing
from crm.contacts.models import Contact, ContactImport
from crm.core.errors import ConflictError, DomainError
from crm.core.services import get_policy
from crm.work.models import Assignment

pytestmark = pytest.mark.django_db


def upload(text, name="book.csv", encoding="utf-8"):
    return SimpleUploadedFile(name, text.encode(encoding), content_type="text/csv")


CSV = (
    "Full Name,E-mail,Mobile,Lead Source,Looking for,Status,Favourite colour\n"
    "Maria Santos,maria@example.test,+63 917 555 0199,Referral,3BR condo,Prospect,blue\n"
    "Jose Cruz,,12,,,,\n"                                   # phone too short -> error
    "Liza Tan,liza@example.test,,Billboard,,,\n"            # unknown source -> kept in source detail
    "Liza T.,LIZA@example.test,,,,,\n"                      # same email as previous row -> duplicate
    ",,,,,,\n"                                              # blank row ignored
)


def test_preview_recognises_columns_validates_and_flags_duplicates(users):
    imp = importing.parse_upload(actor=users["ana"], upload=upload(CSV), destination="me", policy=get_policy())
    assert imp.columns["Full Name"] == "display_name" and "Favourite colour" not in imp.columns
    assert imp.filename == "book.csv"
    assert imp.rows[1]["errors"] == ["Phone: Enter a phone number with at least 6 digits."]
    statuses = [r["status"] for r in imp.rows]
    assert statuses == ["ready", "error", "ready", "duplicate"]
    assert "(source: Billboard)" in imp.rows[2]["data"]["source_detail"]
    assert Contact.objects.count() == 0  # preview adds nothing


def test_run_creates_contacts_for_importer_with_lifecycle_and_skips_duplicates(users):
    imp = importing.parse_upload(actor=users["ana"], upload=upload(CSV), destination="me", policy=get_policy())
    imp = importing.run_import(imp, actor=users["ana"], include_duplicates=False)
    assert imp.summary == {"created": 2, "skipped": 1, "errors": 1}
    maria = Contact.objects.get(email="maria@example.test")
    assert maria.lifecycle == "prospect" and maria.source.code == "referral"
    assert Assignment.objects.get(contact=maria).user == users["ana"]


def test_import_runs_only_once(users):
    imp = importing.parse_upload(actor=users["ana"], upload=upload(CSV), destination="me", policy=get_policy())
    importing.run_import(imp, actor=users["ana"], include_duplicates=True)
    with pytest.raises(ConflictError):
        importing.run_import(ContactImport.objects.get(pk=imp.pk), actor=users["ana"], include_duplicates=True)
    assert Contact.objects.count() == 3


def test_existing_contact_is_flagged_as_duplicate(users, make_contact):
    make_contact("Maria Santos", email="maria@example.test")
    imp = importing.parse_upload(actor=users["ana"], upload=upload(CSV), destination="me", policy=get_policy())
    assert imp.rows[0]["status"] == "duplicate" and imp.rows[0]["duplicates"][0]["name"] == "Maria Santos"


def test_pool_import_and_first_last_name_columns(users, pool):
    text = "First name;Last name;Phone\nAna;Lopez;0917 555 0100\n"
    imp = importing.parse_upload(actor=users["cora"], upload=upload(text), destination="pool", pool=pool, policy=get_policy())
    importing.run_import(imp, actor=users["cora"], include_duplicates=False)
    c = Contact.objects.get(display_name="Ana Lopez")
    assert Assignment.objects.get(contact=c).pool == pool


@pytest.mark.parametrize("text,name,message", [
    ("Email\nx@example.test\n", "a.csv", "No name column"),
    ("", "a.csv", "empty"),
    ("Name\nX\n", "book.xlsx", "Save the spreadsheet as CSV"),
])
def test_bad_files_are_explained(users, text, name, message):
    with pytest.raises(DomainError) as err:
        importing.parse_upload(actor=users["ana"], upload=upload(text, name), destination="me", policy=get_policy())
    assert message in err.value.message


def test_windows_encoded_file_and_export_formula_guard(users):
    text = "Name,Notes\nJosé Niño,'=1+1\n"
    imp = importing.parse_upload(actor=users["ana"], upload=upload(text, encoding="cp1252"), destination="me", policy=get_policy())
    assert imp.rows[0]["data"]["display_name"] == "José Niño" and imp.rows[0]["data"]["notes"] == "=1+1"


def test_only_uploader_can_run(users):
    imp = importing.parse_upload(actor=users["ana"], upload=upload(CSV), destination="me", policy=get_policy())
    with pytest.raises(DomainError):
        importing.run_import(imp, actor=users["ben"], include_duplicates=False)


def test_import_screens(client, users):
    client.force_login(users["ana"])
    assert client.get("/contacts/import/").status_code == 200
    assert b"Name,Email" in client.get("/contacts/import/template.csv").content
    r = client.post("/contacts/import/", {"file": upload(CSV), "destination": "me"})
    assert r.status_code == 302
    page = client.get(r["Location"]).content.decode()
    assert "Ready to add" in page and "Phone" in page
    r = client.post(r["Location"], {"action": "run"})
    assert Contact.objects.count() == 2
