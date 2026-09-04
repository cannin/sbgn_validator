# Native R backend

The R package is a direct Schematron interpreter with a deliberately small
Rcpp boundary. `schematron_compile()` parses the original schema into C++ value
types and compiles its XPath expressions once. `schematron_validate()` parses a
document securely, evaluates the selected phase, and returns SVRL-aligned
normalized findings.

The C++ layer uses libxml2 for XML, namespaces, compiled XPath 1 expressions,
variables, and extension registration. Its profile layer supplies the required
XSLT `current()` context, atomized `distinct-values()`, and `current-time()`.
Raw libxml2 pointers remain behind RAII wrappers and are never exposed to R.

The package does not import CEL code and does not invoke Rust, Java, Python, a
subprocess, or a service. Rcpp and the platform libxml2 library are its only
native integration dependencies. Normal installation is `R CMD INSTALL r`.
The package includes portable configure scripts and passes `R CMD build` and
`R CMD check --no-manual`.

Thread safety is conservative: compiled schemas are immutable, but each
validation creates its own document and XPath contexts. Do not concurrently
call the same R external pointer from multiple R threads.
