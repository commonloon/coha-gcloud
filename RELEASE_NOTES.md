# Release Notes — 2026-03-12

## Summary

This release is a significant performance and reliability overhaul of the backend,
plus a new admin interface for managing observation data.

---

## Performance improvements

### Summary files updated on save, not on read

Previously, the `/map` and `/data` endpoints detected new data by listing every
file in the GCS bucket and comparing timestamps, then rebuilt the summary CSVs by
reading every individual observation file.  With hundreds of files accumulated over
six survey years this was slow and the cost grew with every new observation.

The summary files (`COHA-data-YYYY.csv` and `COHA-data-all-years.csv`) are now
kept current by the `/save` endpoint itself: each successful save appends the new
row directly to both summary files.  `/map` and `/data` simply read the summary —
no bucket listing, no individual file reads.

The same targeted approach is used for deletions: the admin delete operation
removes matching rows from both summary files without re-reading all individual
files.

### Concurrency safety

Appending to a shared file from multiple Cloud Run instances requires care.
All summary updates use GCS **generation-match conditional writes**: a write that
would overwrite a concurrent update is rejected, and the operation retries with a
fresh read.  This guarantees that no observation is lost from the summary even if
two surveyors save at the same moment.

Individual observation files (one per observation, with a unique filename encoding
quadrat, station, and timestamp) remain the canonical data store.  The summary
files are derived caches; if they ever become stale the Force Full Regeneration
admin action rebuilds them correctly from the individual files.

### Module-level GCS client

The Google Cloud Storage client is now created once per Cloud Run instance rather
than on every request, eliminating repeated authentication overhead.

### Direct use of blob objects from list_blobs

`get_data()` previously listed all blobs to collect filenames, then re-fetched each
blob by name to read its content.  It now reads content directly from the blob
objects returned by `list_blobs`, halving the number of GCS API calls during full
regeneration.

---

## New: Admin interface (`/admin/`)

A password-protected admin page provides tools for managing observation data.

- **Year selector** — browse individual observation files by survey year
- **View** — inspect the raw CSV content of any individual file
- **Delete** — remove a bad observation; summaries are updated immediately
- **Force Full Regeneration** — rebuild all summary files from individual observation
  files (recovery tool; use after any manual changes to the bucket)

Access requires HTTP Basic Auth.  Set the password via the `COHA_ADMIN_PASSWORD`
Cloud Run environment variable.

---

## New: Configurable storage bucket (`COHA_BUCKET_NAME`)

The GCS bucket name can now be overridden via the `COHA_BUCKET_NAME` environment
variable (default: `coha-data`).  This allows a test deployment to point at a
separate bucket without any code changes.

---

## Bug fixes

### `coha-map.js` — `year` variable out of scope in catch block

`year` was declared with `let` inside the `try` block of `show_year()`, making it
inaccessible in the `catch` block.  When `AdvancedMarkerElement` failed for any
reason the fallback call to `fallbackToStandardMarkers(year)` threw a second
`ReferenceError`, preventing the map from rendering at all.  `year` is now declared
before the `try` block.

### `coha-map.html` — year dropdown always showed last option as selected

The Jinja2 loop variable was named `year`, shadowing the template variable of the
same name.  The condition `{% if year == year|string %}` was therefore always true,
causing every `<option>` to carry the `selected` attribute (browsers resolve this
by selecting the last one).  The loop variable is now `y`.

### `coha.js` — cloud/wind/noise validation used JS `in` operator on arrays

`val in ["0","1","2","3","4"]` tests whether `val` is a valid array *index*, not
whether it is a member of the array.  The code happened to produce correct results
by coincidence (valid values `"0"`–`"4"` are also valid indices of a 5-element
array), but the intent was membership testing.  Replaced with `.includes()`.

### `main.py` — all-years summary sort order restored

The all-years summary is now written sorted by year first (then quadrat / station /
timestamp within each year), matching the order produced by previous releases.

---

## Code quality

- Extracted `_csv_to_string()`, `_year_from_filename()`, and
  `_iter_observation_blobs()` helpers to eliminate repeated patterns
- Pre-compiled `DATA_FILE_NAME_PATTERN` regex at module level
- `csv_write_to_google_cloud` returns `(bool, str)` instead of a string whose
  content had to be inspected to determine success
- Removed dead code: `is_there_new_data()`, `regenerate_current_year()`,
  `load_yearly_data()`, `show_map_regen_all` route, bucket-creation logic
- `get_cookie_data()` uses `.get()` defaults instead of manual None checks
