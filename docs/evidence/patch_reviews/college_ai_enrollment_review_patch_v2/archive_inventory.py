"""Write exact archive inventory and a review diff without applying the patch."""
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

review = Path(__file__).resolve().parent
repository = review.parents[3]
archive = review / "COLLEGE_AI_ENROLLMENT_REVIEW_PATCH_V2.zip"
records = []
diff = []
with zipfile.ZipFile(archive) as bundle:
    for entry in bundle.infolist():
        contents = bundle.read(entry)
        extracted = review / "source" / entry.filename
        assert extracted.read_bytes() == contents, entry.filename
        active = repository / entry.filename
        status = "replace" if active.exists() else "add"
        records.append({"path": entry.filename, "bytes": len(contents), "sha256": hashlib.sha256(contents).hexdigest(), "change": status})
        previous = active.read_text(encoding="utf-8").splitlines(keepends=True) if active.exists() else []
        proposed = contents.decode("utf-8").splitlines(keepends=True)
        diff.extend(difflib.unified_diff(previous, proposed, fromfile="a/" + entry.filename, tofile="b/" + entry.filename))
(review / "inventory.json").write_text(json.dumps({"archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "files": records}, indent=2), encoding="utf-8")
(review / "patch_vs_checkout.diff").write_text("".join(diff), encoding="utf-8")
print(f"Archive verified: {len(records)} unchanged extracted files; {sum(r['change'] == 'replace' for r in records)} replacements, {sum(r['change'] == 'add' for r in records)} additions")
