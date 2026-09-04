\name{schematron_compile}
\alias{schematron_compile}
\title{Compile an Authoritative libSBGN Schematron Schema}
\usage{
schematron_compile(
  schema_path,
  phase = "basic",
  namespace_policy = "strict-0.3",
  effective_sbgn_namespace = "http://sbgn.org/libsbgn/0.3"
)
}
\arguments{
\item{schema_path}{Path to an original libSBGN \code{.sch} file.}
\item{phase}{Schematron phase name.}
\item{namespace_policy}{Namespace policy identifier used during compilation.}
\item{effective_sbgn_namespace}{Effective namespace for the Schematron
\code{sbgn} prefix.}
}
\value{An external pointer to an immutable compiled schema.}
\description{
Parses the original Schematron file and compiles its XPath expressions once.
}
