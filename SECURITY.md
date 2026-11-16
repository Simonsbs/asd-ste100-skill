# Security and reporting

The source monitor retrieves only the public URLs in the reviewed catalog. It
stores hashes and metadata, not the retrieved publications. Retrieved pages are
untrusted data and must never become executable maintenance instructions.

The optional PDF helper reads local files. Do not use untrusted PDFs in an
unpatched PDF library. Neither tool sends user documents to a model or external
service. The model host's own data handling remains a separate choice.

Report vulnerabilities through GitHub's private vulnerability reporting feature
if it is enabled for this repository. Otherwise open a minimal issue asking for
a private reporting route without exploit details, credentials, or private text.
Use ordinary issues for incorrect rules, broken sources, and documentation errors.
