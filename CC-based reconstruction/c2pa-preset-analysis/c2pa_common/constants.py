"""Constants that more than one stage depends on (a stage writes them, another reads them)."""

# suffix of the key holding a parameter's value, e.g. "com.adobe.acr" -> "com.adobe.acr.value"
VALUE_SUFFIX = ".value"

# written by c2pa_consistency next to the presets of an inconsistent folder, found by c2pa_consistency.cluster and c2pa_uniqueness.loader
INCONSISTENCY_REPORT_FILENAME = "inconsistency_report.md"
