# Legacy snapshot fixtures

legacy_creators.json.gz is a deterministic gzip-compressed JSON object containing two HTML test fixtures.

Provenance: public W17_02 Creator source at ad92e4bed71d8b8ccb19c6b1c8868b7bb14de132, captured once during project separation. Only the browser-storage namespace is adapted from w17_02 to w17_04 so these fixtures exercise supported legacy serialization *within this project*, rather than importing the old project's storage.

The fixture preserves real historical serialization behavior for migration tests (text edits, section order, tags and deleted cards). Tests extract it only to an isolated temporary test server. It is test data, not an active page or destination Git history. The new repository has no parent commits or remote dependency on W17_02. Running tests requires neither the source checkout nor its Git commits.
