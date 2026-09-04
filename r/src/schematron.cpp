#include <Rcpp.h>

#include <libxml/parser.h>
#include <libxml/tree.h>
#include <libxml/xpath.h>
#include <libxml/xpathInternals.h>

#include <algorithm>
#include <chrono>
#include <cctype>
#include <ctime>
#include <iomanip>
#include <map>
#include <memory>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

namespace {

constexpr const char* kIsoNamespace = "http://purl.oclc.org/dsdl/schematron";
constexpr const char* kSbgnMl03 = "http://sbgn.org/libsbgn/0.3";
constexpr const char* kSbgnMl02 = "http://sbgn.org/libsbgn/0.2";
constexpr const char* kCompatibilityPhase = "basic-allow-sbgnml-0.2";

struct XmlDocDeleter {
    void operator()(xmlDocPtr value) const {
        if (value != nullptr) {
            xmlFreeDoc(value);
        }
    }
};

struct XPathContextDeleter {
    void operator()(xmlXPathContextPtr value) const {
        if (value != nullptr) {
            xmlXPathFreeContext(value);
        }
    }
};

struct XPathObjectDeleter {
    void operator()(xmlXPathObjectPtr value) const {
        if (value != nullptr) {
            xmlXPathFreeObject(value);
        }
    }
};

using XmlDocument = std::unique_ptr<xmlDoc, XmlDocDeleter>;
using XPathContext = std::unique_ptr<xmlXPathContext, XPathContextDeleter>;
using XPathObject = std::unique_ptr<xmlXPathObject, XPathObjectDeleter>;

std::string xml_string(const xmlChar* value) {
    return value == nullptr ? "" : reinterpret_cast<const char*>(value);
}

std::string property(xmlNodePtr node, const char* name) {
    xmlChar* raw = xmlGetProp(node, BAD_CAST name);
    std::string value = xml_string(raw);
    xmlFree(raw);
    return value;
}

bool is_iso_element(xmlNodePtr node, const char* name) {
    return node != nullptr && node->type == XML_ELEMENT_NODE &&
           xmlStrEqual(node->name, BAD_CAST name) && node->ns != nullptr &&
           xmlStrEqual(node->ns->href, BAD_CAST kIsoNamespace);
}

std::string normalize_space(const std::string& value) {
    std::ostringstream output;
    bool pending_space = false;
    bool emitted = false;
    for (unsigned char item : value) {
        if (std::isspace(item) != 0) {
            pending_space = emitted;
        } else {
            if (pending_space) {
                output << ' ';
            }
            output << static_cast<char>(item);
            emitted = true;
            pending_space = false;
        }
    }
    static const std::regex clock(
        R"(\b(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-][0-2]\d:[0-5]\d)?\b)");
    return std::regex_replace(output.str(), clock, "<CURRENT_TIME>");
}

std::vector<std::string> split_words(const std::string& value) {
    std::istringstream input(value);
    std::vector<std::string> words;
    std::string word;
    while (input >> word) {
        words.push_back(word);
    }
    return words;
}

std::string basename(const std::string& path) {
    const std::size_t slash = path.find_last_of("/\\");
    return slash == std::string::npos ? path : path.substr(slash + 1);
}

class CompiledExpression {
  public:
    CompiledExpression() = default;

    explicit CompiledExpression(std::string source) : source_(std::move(source)) {
        // libxml2 implements XPath 1.0. This is the sole XPath-2 path syntax in
        // the pinned corpus; lower it to its XPath-1-equivalent AST form.
        compiled_source_ = source_ == "../local-name()" ? "local-name(..)" : source_;
        expression_ = xmlXPathCompile(BAD_CAST compiled_source_.c_str());
        if (expression_ == nullptr) {
            throw std::runtime_error("XPATH_PARSE_ERROR: " + source_);
        }
    }

    ~CompiledExpression() {
        if (expression_ != nullptr) {
            xmlXPathFreeCompExpr(expression_);
        }
    }

    CompiledExpression(const CompiledExpression&) = delete;
    CompiledExpression& operator=(const CompiledExpression&) = delete;

    CompiledExpression(CompiledExpression&& other) noexcept
        : source_(std::move(other.source_)),
          compiled_source_(std::move(other.compiled_source_)), expression_(other.expression_) {
        other.expression_ = nullptr;
    }

    CompiledExpression& operator=(CompiledExpression&& other) noexcept {
        if (this != &other) {
            if (expression_ != nullptr) {
                xmlXPathFreeCompExpr(expression_);
            }
            source_ = std::move(other.source_);
            compiled_source_ = std::move(other.compiled_source_);
            expression_ = other.expression_;
            other.expression_ = nullptr;
        }
        return *this;
    }

    xmlXPathCompExprPtr get() const { return expression_; }
    const std::string& source() const { return source_; }

  private:
    std::string source_;
    std::string compiled_source_;
    xmlXPathCompExprPtr expression_ = nullptr;
};

struct MessagePart {
    bool expression = false;
    std::string text;
    std::unique_ptr<CompiledExpression> compiled;
};

struct LetBinding {
    std::string name;
    CompiledExpression value;
};

struct Check {
    std::string kind;
    std::string id;
    std::string role;
    std::string flag;
    CompiledExpression test;
    std::vector<std::string> diagnostic_ids;
    std::vector<MessagePart> message;
};

struct Rule {
    std::string context_source;
    CompiledExpression context;
    std::vector<LetBinding> lets;
    std::vector<Check> checks;
};

struct Pattern {
    std::string id;
    std::vector<Rule> rules;
};

struct Diagnostic {
    std::string id;
    std::vector<MessagePart> message;
};

struct CompiledSchema {
    std::string schema_name;
    std::string phase;
    std::map<std::string, std::string> namespaces;
    std::set<std::string> active_patterns;
    std::vector<Pattern> patterns;
    std::map<std::string, Diagnostic> diagnostics;
    std::vector<std::string> diagnostic_order;
};

struct EvaluationRuntime {
    xmlNodePtr schematron_current = nullptr;
};

void current_function(xmlXPathParserContextPtr context, int arguments) {
    if (arguments != 0) {
        xmlXPathSetArityError(context);
        return;
    }
    auto* runtime = static_cast<EvaluationRuntime*>(context->context->userData);
    if (runtime == nullptr || runtime->schematron_current == nullptr) {
        xmlXPathErr(context, XPATH_INVALID_CTXT);
        return;
    }
    valuePush(context, xmlXPathNewNodeSet(runtime->schematron_current));
}

void distinct_values_function(xmlXPathParserContextPtr context, int arguments) {
    if (arguments != 1) {
        xmlXPathSetArityError(context);
        return;
    }
    xmlXPathObjectPtr input = valuePop(context);
    if (input == nullptr || input->type != XPATH_NODESET) {
        if (input != nullptr) {
            xmlXPathFreeObject(input);
        }
        xmlXPathErr(context, XPATH_INVALID_TYPE);
        return;
    }

    xmlXPathObjectPtr output = xmlXPathNewNodeSet(nullptr);
    std::unordered_set<std::string> seen;
    if (input->nodesetval != nullptr) {
        for (int index = 0; index < input->nodesetval->nodeNr; ++index) {
            xmlNodePtr node = input->nodesetval->nodeTab[index];
            xmlChar* raw = xmlXPathCastNodeToString(node);
            const std::string value = xml_string(raw);
            xmlFree(raw);
            if (seen.insert(value).second) {
                xmlXPathNodeSetAdd(output->nodesetval, node);
            }
        }
    }
    xmlXPathFreeObject(input);
    valuePush(context, output);
}

void current_time_function(xmlXPathParserContextPtr context, int arguments) {
    if (arguments != 0) {
        xmlXPathSetArityError(context);
        return;
    }
    const auto now = std::chrono::system_clock::now();
    const std::time_t time = std::chrono::system_clock::to_time_t(now);
    std::tm local{};
#ifdef _WIN32
    localtime_s(&local, &time);
#else
    localtime_r(&time, &local);
#endif
    std::ostringstream value;
    value << std::put_time(&local, "%H:%M:%S");
    valuePush(context, xmlXPathNewString(BAD_CAST value.str().c_str()));
}

void register_context(XPathContext& context, const CompiledSchema& schema,
                      EvaluationRuntime* runtime) {
    context->userData = runtime;
    for (const auto& [prefix, uri] : schema.namespaces) {
        if (xmlXPathRegisterNs(context.get(), BAD_CAST prefix.c_str(), BAD_CAST uri.c_str()) != 0) {
            throw std::runtime_error("XPATH_STATIC_ERROR: cannot register namespace " + prefix);
        }
    }
    if (xmlXPathRegisterFunc(context.get(), BAD_CAST "current", current_function) != 0 ||
        xmlXPathRegisterFunc(context.get(), BAD_CAST "distinct-values",
                             distinct_values_function) != 0 ||
        xmlXPathRegisterFunc(context.get(), BAD_CAST "current-time", current_time_function) != 0) {
        throw std::runtime_error("XPATH_STATIC_ERROR: cannot register compatibility functions");
    }
}

XPathObject evaluate(const CompiledExpression& expression, xmlXPathContextPtr context) {
    xmlXPathObjectPtr result = xmlXPathCompiledEval(expression.get(), context);
    if (result == nullptr) {
        throw std::runtime_error("XPATH_DYNAMIC_ERROR: " + expression.source());
    }
    return XPathObject(result);
}

std::vector<MessagePart> parse_message(xmlNodePtr parent) {
    std::vector<MessagePart> parts;
    for (xmlNodePtr child = parent->children; child != nullptr; child = child->next) {
        if (child->type == XML_TEXT_NODE || child->type == XML_CDATA_SECTION_NODE) {
            const std::string text = xml_string(child->content);
            if (!text.empty()) {
                parts.push_back(MessagePart{false, text, nullptr});
            }
        } else if (is_iso_element(child, "value-of")) {
            const std::string select = property(child, "select");
            if (select.empty()) {
                throw std::runtime_error("SCHEMATRON_SCHEMA_ERROR: value-of requires select");
            }
            parts.push_back(
                MessagePart{true, select, std::make_unique<CompiledExpression>(select)});
        } else if (is_iso_element(child, "name")) {
            const std::string path = property(child, "path");
            const std::string source = "name(" + (path.empty() ? std::string(".") : path) + ")";
            parts.push_back(
                MessagePart{true, source, std::make_unique<CompiledExpression>(source)});
        } else if (child->type == XML_ELEMENT_NODE) {
            throw std::runtime_error("SCHEMATRON_UNSUPPORTED_FEATURE: message child " +
                                     xml_string(child->name));
        }
    }
    return parts;
}

CompiledSchema parse_schema(const std::string& schema_path, const std::string& requested_phase,
                            const std::string& namespace_policy,
                            const std::string& effective_sbgn_namespace) {
    XmlDocument document(xmlReadFile(schema_path.c_str(), nullptr,
                                     XML_PARSE_NONET | XML_PARSE_NOBLANKS));
    if (!document) {
        throw std::runtime_error("SCHEMATRON_PARSE_ERROR: " + schema_path);
    }
    xmlNodePtr root = xmlDocGetRootElement(document.get());
    if (!is_iso_element(root, "schema")) {
        throw std::runtime_error("SCHEMATRON_SCHEMA_ERROR: root must be iso:schema");
    }

    CompiledSchema schema;
    schema.schema_name = basename(schema_path);
    schema.phase = requested_phase.empty() ? property(root, "defaultPhase") : requested_phase;
    if (schema.phase.empty()) {
        schema.phase = "#ALL";
    }

    bool compatibility_phase_found = false;
    for (xmlNodePtr child = root->children; child != nullptr; child = child->next) {
        if (is_iso_element(child, "phase") &&
            property(child, "id") == kCompatibilityPhase) {
            compatibility_phase_found = true;
            break;
        }
    }
    if (namespace_policy == "allow-sbgnml-0.2" && schema.phase == "basic" &&
        compatibility_phase_found) {
        schema.phase = kCompatibilityPhase;
    }

    bool phase_found = schema.phase == "#ALL";
    int sbgn_binding_count = 0;
    for (xmlNodePtr child = root->children; child != nullptr; child = child->next) {
        if (is_iso_element(child, "ns")) {
            const std::string prefix = property(child, "prefix");
            std::string uri = property(child, "uri");
            if (prefix == "sbgn") {
                sbgn_binding_count += 1;
                if (effective_sbgn_namespace == kSbgnMl02) {
                    if (uri != kSbgnMl03 && uri != kSbgnMl02) {
                        throw std::runtime_error(
                            "SCHEMATRON_NAMESPACE_ERROR: unsafe sbgn binding " + uri);
                    }
                    uri = kSbgnMl02;
                }
            }
            schema.namespaces.emplace(prefix, uri);
        } else if (is_iso_element(child, "phase") && property(child, "id") == schema.phase) {
            phase_found = true;
            for (xmlNodePtr active = child->children; active != nullptr; active = active->next) {
                if (is_iso_element(active, "active")) {
                    schema.active_patterns.insert(property(active, "pattern"));
                }
            }
        }
    }
    if (effective_sbgn_namespace == kSbgnMl02 && sbgn_binding_count != 1) {
        throw std::runtime_error(
            "SCHEMATRON_NAMESPACE_ERROR: expected one sbgn namespace binding");
    }
    if (!phase_found) {
        throw std::runtime_error("PHASE_NOT_FOUND: " + schema.phase);
    }

    for (xmlNodePtr child = root->children; child != nullptr; child = child->next) {
        if (is_iso_element(child, "pattern")) {
            Pattern pattern;
            pattern.id = property(child, "id");
            for (xmlNodePtr rule_node = child->children; rule_node != nullptr;
                 rule_node = rule_node->next) {
                if (!is_iso_element(rule_node, "rule")) {
                    continue;
                }
                const std::string context_source = property(rule_node, "context");
                if (context_source.empty()) {
                    throw std::runtime_error("SCHEMATRON_SCHEMA_ERROR: rule requires context");
                }
                const std::string selector = context_source.front() == '/'
                                                 ? context_source
                                                 : "//" + context_source;
                Rule rule{context_source, CompiledExpression(selector), {}, {}};
                for (xmlNodePtr item = rule_node->children; item != nullptr; item = item->next) {
                    if (is_iso_element(item, "let")) {
                        const std::string name = property(item, "name");
                        const std::string value = property(item, "value");
                        rule.lets.push_back(LetBinding{name, CompiledExpression(value)});
                    } else if (is_iso_element(item, "assert") || is_iso_element(item, "report")) {
                        const bool assertion = is_iso_element(item, "assert");
                        const std::string test = property(item, "test");
                        rule.checks.push_back(Check{
                            assertion ? "assert" : "report", property(item, "id"),
                            property(item, "role"), property(item, "flag"),
                            CompiledExpression(test), split_words(property(item, "diagnostics")),
                            parse_message(item)});
                    } else if (item->type == XML_ELEMENT_NODE) {
                        throw std::runtime_error("SCHEMATRON_UNSUPPORTED_FEATURE: rule child " +
                                                 xml_string(item->name));
                    }
                }
                pattern.rules.push_back(std::move(rule));
            }
            schema.patterns.push_back(std::move(pattern));
        } else if (is_iso_element(child, "diagnostics")) {
            for (xmlNodePtr diagnostic_node = child->children; diagnostic_node != nullptr;
                 diagnostic_node = diagnostic_node->next) {
                if (is_iso_element(diagnostic_node, "diagnostic")) {
                    Diagnostic diagnostic{property(diagnostic_node, "id"),
                                          parse_message(diagnostic_node)};
                    schema.diagnostic_order.push_back(diagnostic.id);
                    schema.diagnostics.emplace(diagnostic.id, std::move(diagnostic));
                }
            }
        } else if (child->type == XML_ELEMENT_NODE && !is_iso_element(child, "title") &&
                   !is_iso_element(child, "phase") && !is_iso_element(child, "ns")) {
            throw std::runtime_error("SCHEMATRON_UNSUPPORTED_FEATURE: schema child " +
                                     xml_string(child->name));
        }
    }
    return schema;
}

std::string xpath_string(const XPathObject& object) {
    if (object->type == XPATH_NODESET && object->nodesetval != nullptr) {
        std::ostringstream output;
        for (int index = 0; index < object->nodesetval->nodeNr; ++index) {
            if (index > 0) {
                output << ' ';
            }
            xmlChar* raw = xmlXPathCastNodeToString(object->nodesetval->nodeTab[index]);
            output << xml_string(raw);
            xmlFree(raw);
        }
        return output.str();
    }
    xmlChar* raw = xmlXPathCastToString(object.get());
    std::string value = xml_string(raw);
    xmlFree(raw);
    return value;
}

std::string render_message(const std::vector<MessagePart>& parts, xmlXPathContextPtr context) {
    std::ostringstream output;
    for (const MessagePart& part : parts) {
        if (part.expression) {
            output << xpath_string(evaluate(*part.compiled, context));
        } else {
            output << part.text;
        }
    }
    return normalize_space(output.str());
}

std::string node_kind(xmlNodePtr node) {
    return node == nullptr ? "" : xml_string(node->name);
}

std::string canonical_location(xmlNodePtr node) {
    if (node == nullptr || node->type == XML_DOCUMENT_NODE) {
        return "";
    }
    int position = 1;
    for (xmlNodePtr sibling = node->prev; sibling != nullptr; sibling = sibling->prev) {
        if (sibling->type == XML_ELEMENT_NODE && xmlStrEqual(sibling->name, node->name) &&
            ((sibling->ns == nullptr && node->ns == nullptr) ||
             (sibling->ns != nullptr && node->ns != nullptr &&
              xmlStrEqual(sibling->ns->href, node->ns->href)))) {
            ++position;
        }
    }
    const std::string prefix = node->ns != nullptr && node->ns->prefix != nullptr
                                   ? xml_string(node->ns->prefix) + ":"
                                   : "";
    return canonical_location(node->parent) + "/" + prefix + node_kind(node) + "[" +
           std::to_string(position) + "]";
}

Rcpp::List validate_schema(const CompiledSchema& schema, const std::string& document_path) {
    XmlDocument document(xmlReadFile(document_path.c_str(), nullptr,
                                     XML_PARSE_NONET | XML_PARSE_NOBLANKS));
    if (!document) {
        throw std::runtime_error("XML_PARSE_ERROR: " + document_path);
    }

    std::vector<Rcpp::List> findings;
    for (const Pattern& pattern : schema.patterns) {
        if (schema.phase != "#ALL" && schema.active_patterns.count(pattern.id) == 0) {
            continue;
        }
        for (const Rule& rule : pattern.rules) {
            EvaluationRuntime selection_runtime;
            XPathContext selection(xmlXPathNewContext(document.get()));
            if (!selection) {
                throw std::runtime_error("INTERNAL_VALIDATOR_ERROR: XPath context allocation");
            }
            register_context(selection, schema, &selection_runtime);
            selection->node = reinterpret_cast<xmlNodePtr>(document.get());
            XPathObject matched = evaluate(rule.context, selection.get());
            if (matched->type != XPATH_NODESET) {
                throw std::runtime_error("XPATH_DYNAMIC_ERROR: rule context is not a node set: " +
                                         rule.context_source);
            }
            std::vector<xmlNodePtr> nodes;
            if (matched->nodesetval != nullptr) {
                for (int index = 0; index < matched->nodesetval->nodeNr; ++index) {
                    nodes.push_back(matched->nodesetval->nodeTab[index]);
                }
            }

            for (xmlNodePtr node : nodes) {
                EvaluationRuntime runtime{node};
                XPathContext context(xmlXPathNewContext(document.get()));
                if (!context) {
                    throw std::runtime_error("INTERNAL_VALIDATOR_ERROR: XPath context allocation");
                }
                register_context(context, schema, &runtime);
                context->node = node;
                for (const LetBinding& binding : rule.lets) {
                    XPathObject value = evaluate(binding.value, context.get());
                    if (xmlXPathRegisterVariable(context.get(), BAD_CAST binding.name.c_str(),
                                                 xmlXPathObjectCopy(value.get())) != 0) {
                        throw std::runtime_error("XPATH_DYNAMIC_ERROR: cannot bind $" +
                                                 binding.name);
                    }
                }

                for (const Check& check : rule.checks) {
                    XPathObject test = evaluate(check.test, context.get());
                    const bool truth = xmlXPathCastToBoolean(test.get()) != 0;
                    const bool fires = check.kind == "assert" ? !truth : truth;
                    if (!fires) {
                        continue;
                    }

                    Rcpp::List diagnostic_references;
                    std::string element_id;
                    const std::set<std::string> selected_diagnostics(
                        check.diagnostic_ids.begin(), check.diagnostic_ids.end());
                    for (const std::string& diagnostic_id : schema.diagnostic_order) {
                        if (selected_diagnostics.count(diagnostic_id) == 0) {
                            continue;
                        }
                        const auto found = schema.diagnostics.find(diagnostic_id);
                        if (found == schema.diagnostics.end()) {
                            throw std::runtime_error("SCHEMATRON_SCHEMA_ERROR: unknown diagnostic " +
                                                     diagnostic_id);
                        }
                        const std::string value = render_message(found->second.message, context.get());
                        diagnostic_references.push_back(Rcpp::List::create(
                            Rcpp::_["diagnostic"] = diagnostic_id,
                            Rcpp::_["text"] = value));
                        if (diagnostic_id == "id" && element_id.empty()) {
                            element_id = value;
                        }
                    }
                    const std::string finding_type =
                        check.kind == "assert" ? "failed-assert" : "successful-report";
                    findings.push_back(Rcpp::List::create(
                        Rcpp::_["id"] = check.id.empty() ? R_NilValue : Rcpp::wrap(check.id),
                        Rcpp::_["type"] = finding_type,
                        Rcpp::_["role"] = check.role.empty() ? R_NilValue : Rcpp::wrap(check.role),
                        Rcpp::_["flag"] = check.flag.empty() ? R_NilValue : Rcpp::wrap(check.flag),
                        Rcpp::_["location"] = canonical_location(node),
                        Rcpp::_["test"] = normalize_space(check.test.source()),
                        Rcpp::_["text"] = render_message(check.message, context.get()),
                        Rcpp::_["diagnostic_references"] = diagnostic_references,
                        Rcpp::_["derived"] = Rcpp::List::create(
                            Rcpp::_["element_id"] =
                                element_id.empty() ? R_NilValue : Rcpp::wrap(element_id),
                            Rcpp::_["element_kind"] = node_kind(node))));
                }
            }
        }
    }

    std::sort(findings.begin(), findings.end(), [](const Rcpp::List& left, const Rcpp::List& right) {
        const std::string left_rule = Rcpp::as<std::string>(left["id"]);
        const std::string right_rule = Rcpp::as<std::string>(right["id"]);
        if (left_rule != right_rule) {
            return left_rule < right_rule;
        }
        const Rcpp::List left_derived = left["derived"];
        const Rcpp::List right_derived = right["derived"];
        const SEXP left_id_value = left_derived["element_id"];
        const SEXP right_id_value = right_derived["element_id"];
        const std::string left_id = Rf_isNull(left_id_value) ? "" : Rcpp::as<std::string>(left_id_value);
        const std::string right_id =
            Rf_isNull(right_id_value) ? "" : Rcpp::as<std::string>(right_id_value);
        if (left_id != right_id) {
            return left_id < right_id;
        }
        return Rcpp::as<std::string>(left["location"]) <
               Rcpp::as<std::string>(right["location"]);
    });

    return Rcpp::List::create(
        Rcpp::_["schema"] = schema.schema_name, Rcpp::_["phase"] = schema.phase,
        Rcpp::_["valid"] = findings.empty(), Rcpp::_["findings"] = Rcpp::wrap(findings),
        Rcpp::_["backend"] = Rcpp::List::create(
            Rcpp::_["language"] = "r", Rcpp::_["implementation"] = "sbgn-validator-r",
            Rcpp::_["implementation_version"] = "0.1.1",
            Rcpp::_["schematron_engine"] = "project-direct-interpreter",
            Rcpp::_["xpath_engine"] = "libxml2",
            Rcpp::_["xpath_version"] = "1.0 plus libSBGN profile extensions",
            Rcpp::_["profile_version"] = "1", Rcpp::_["native_schematron"] = true));
}

}  // namespace

//' Compile an original libSBGN Schematron schema.
//'
//' @param schema_path Path to the authoritative schema.
//' @param phase Schematron phase to activate.
//' @param namespace_policy Namespace policy identifier.
//' @param effective_sbgn_namespace Effective namespace for the `sbgn` prefix.
//' @return An external pointer to a compiled schema.
// [[Rcpp::export]]
SEXP schematron_compile_cpp(const std::string& schema_path, const std::string& phase,
                            const std::string& namespace_policy,
                            const std::string& effective_sbgn_namespace) {
    try {
        auto* schema = new CompiledSchema(parse_schema(
            schema_path, phase, namespace_policy, effective_sbgn_namespace));
        Rcpp::XPtr<CompiledSchema> pointer(schema, true);
        pointer.attr("class") = Rcpp::CharacterVector::create("sbgn_validator_schema");
        return pointer;
    } catch (const std::exception& error) {
        Rcpp::stop("%s", error.what());
    }
}

//' Validate an SBGN-ML document with a compiled schema.
//'
//' @param schema_pointer External pointer returned by `schematron_compile_cpp`.
//' @param document_path Path to the SBGN-ML document.
//' @return A normalized validation report.
// [[Rcpp::export]]
Rcpp::List schematron_validate_cpp(SEXP schema_pointer, const std::string& document_path) {
    try {
        Rcpp::XPtr<CompiledSchema> schema(schema_pointer);
        return validate_schema(*schema, document_path);
    } catch (const std::exception& error) {
        Rcpp::stop("%s", error.what());
    }
}

//' Inspect the root namespace and language of the first SBGN map.
//'
//' @param document_path Path to the SBGN-ML document.
//' @return The root namespace and SBGN map language.
// [[Rcpp::export]]
Rcpp::List sbgn_document_info_cpp(const std::string& document_path) {
    XmlDocument document(xmlReadFile(document_path.c_str(), nullptr,
                                     XML_PARSE_NONET | XML_PARSE_NOBLANKS));
    if (!document) {
        Rcpp::stop("XML_PARSE_ERROR: %s", document_path.c_str());
    }
    xmlNodePtr root = xmlDocGetRootElement(document.get());
    if (root == nullptr || !xmlStrEqual(root->name, BAD_CAST "sbgn")) {
        Rcpp::stop("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing");
    }
    const std::string document_namespace =
        root->ns == nullptr ? "" : xml_string(root->ns->href);
    for (xmlNodePtr child = root == nullptr ? nullptr : root->children; child != nullptr;
         child = child->next) {
        const std::string child_namespace =
            child->ns == nullptr ? "" : xml_string(child->ns->href);
        if (child->type == XML_ELEMENT_NODE && xmlStrEqual(child->name, BAD_CAST "map") &&
            child_namespace == document_namespace) {
            const std::string language = property(child, "language");
            if (!language.empty()) {
                return Rcpp::List::create(
                    Rcpp::_["namespace"] = document_namespace,
                    Rcpp::_["language"] = language);
            }
        }
    }
    Rcpp::stop("SCHEMATRON_SCHEMA_ERROR: SBGN map language is missing");
}
