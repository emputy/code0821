from app.collector.dates import normalize, _first_date
cases = [
    ("20 AUG 2026", "2026-08-20"),
    ("14 March 2025", "2025-03-14"),
    ("2026-08-20T10:00:00Z", "2026-08-20"),
    ("20.08.2026", "2026-08-20"),
    ("Publication date: 20 August 2026", "2026-08-20"),
    ("NO. 1 OF 2026 FOR SPECTRUM ASSIGNMENT", ""),  # title noise must NOT match
]
ok = True
for raw, want in cases:
    got = normalize(raw)
    status = "OK " if got == want else "FAIL"
    if got != want:
        ok = False
    print(f"{status} {raw!r} -> {got!r} (want {want!r})")
print("ALL OK" if ok else "SOME FAILED")
