// Package validator directly interprets the Schematron constructs used by libSBGN.
package validator

import (
	"context"
	"encoding/xml"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/cannin/sbgn_validator/go/internal/rules"
	helium "github.com/lestrrat-go/helium"
	"github.com/lestrrat-go/helium/xpath3"
)

const profileVersion = "1"

const (
	sbgnML03           = "http://sbgn.org/libsbgn/0.3"
	sbgnML02           = "http://sbgn.org/libsbgn/0.2"
	compatibilityPhase = "basic-allow-sbgnml-0.2"
)

// NamespacePolicy controls which SBGN-ML document namespaces are accepted.
type NamespacePolicy int

const (
	// Strict03 accepts only SBGN-ML 0.3.
	Strict03 NamespacePolicy = iota
	// AllowSBGNML02 accepts SBGN-ML 0.3 and legacy SBGN-ML 0.2.
	AllowSBGNML02
)

func (policy NamespacePolicy) effectiveNamespace(documentNamespace string) (string, error) {
	if documentNamespace == sbgnML03 {
		return sbgnML03, nil
	}
	if policy == AllowSBGNML02 && documentNamespace == sbgnML02 {
		return sbgnML02, nil
	}
	expected := sbgnML03
	if policy == AllowSBGNML02 {
		expected += " or " + sbgnML02
	}
	found := documentNamespace
	if found == "" {
		found = "<missing>"
	}
	return "", fmt.Errorf("SBGN_NAMESPACE_ERROR: expected %s; found %s", expected, found)
}

var clockPattern = regexp.MustCompile(`\b(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-][0-2]\d:[0-5]\d)?\b`)

// BackendInfo describes the native implementation used for a report.
type BackendInfo struct {
	Language              string `json:"language"`
	Implementation        string `json:"implementation"`
	ImplementationVersion string `json:"implementation_version"`
	SchematronEngine      string `json:"schematron_engine"`
	XPathEngine           string `json:"xpath_engine"`
	XPathVersion          string `json:"xpath_version"`
	ProfileVersion        string `json:"profile_version"`
	NativeSchematron      bool   `json:"native_schematron"`
}

// DiagnosticReference is one ordered SVRL diagnostic-reference value.
type DiagnosticReference struct {
	Diagnostic string `json:"diagnostic"`
	Text       string `json:"text"`
}

// DerivedIdentity contains stable SBGN identity derived from a finding.
type DerivedIdentity struct {
	ElementID   *string `json:"element_id"`
	ElementKind string  `json:"element_kind"`
}

// Finding is the SVRL-aligned representation of one fired check.
type Finding struct {
	ID                   *string               `json:"id"`
	Type                 string                `json:"type"`
	Role                 *string               `json:"role"`
	Flag                 *string               `json:"flag"`
	Location             string                `json:"location"`
	Test                 string                `json:"test"`
	Text                 string                `json:"text"`
	DiagnosticReferences []DiagnosticReference `json:"diagnostic_references"`
	Derived              DerivedIdentity       `json:"derived"`
}

// Report is the deterministic cross-runtime validation result.
type Report struct {
	Schema   string       `json:"schema"`
	Phase    string       `json:"phase"`
	Valid    bool         `json:"valid"`
	Findings []Finding    `json:"findings"`
	Backend  *BackendInfo `json:"backend,omitempty"`
}

type namespaceXML struct {
	Prefix string `xml:"prefix,attr"`
	URI    string `xml:"uri,attr"`
}

type activeXML struct {
	Pattern string `xml:"pattern,attr"`
}

type phaseXML struct {
	ID     string      `xml:"id,attr"`
	Active []activeXML `xml:"active"`
}

type letXML struct {
	Name  string `xml:"name,attr"`
	Value string `xml:"value,attr"`
}

type messagePartXML struct {
	Expression bool
	Value      string
}

type checkXML struct {
	ID          string
	Role        string
	Flag        string
	Test        string
	Diagnostics []string
	Message     []messagePartXML
}

func (value *checkXML) UnmarshalXML(decoder *xml.Decoder, start xml.StartElement) error {
	for _, attribute := range start.Attr {
		switch attribute.Name.Local {
		case "id":
			value.ID = attribute.Value
		case "role":
			value.Role = attribute.Value
		case "flag":
			value.Flag = attribute.Value
		case "test":
			value.Test = attribute.Value
		case "diagnostics":
			value.Diagnostics = strings.Fields(attribute.Value)
		}
	}
	message, err := decodeMessage(decoder, start)
	value.Message = message
	return err
}

type diagnosticXML struct {
	ID      string
	Message []messagePartXML
}

func (value *diagnosticXML) UnmarshalXML(decoder *xml.Decoder, start xml.StartElement) error {
	for _, attribute := range start.Attr {
		if attribute.Name.Local == "id" {
			value.ID = attribute.Value
		}
	}
	message, err := decodeMessage(decoder, start)
	value.Message = message
	return err
}

func decodeMessage(decoder *xml.Decoder, start xml.StartElement) ([]messagePartXML, error) {
	var parts []messagePartXML
	for {
		token, err := decoder.Token()
		if err != nil {
			return nil, err
		}
		switch item := token.(type) {
		case xml.CharData:
			parts = append(parts, messagePartXML{Value: string(item)})
		case xml.StartElement:
			if item.Name.Local != "value-of" && item.Name.Local != "name" {
				return nil, fmt.Errorf("SCHEMATRON_UNSUPPORTED_FEATURE: message child %s", item.Name.Local)
			}
			attributeName := "select"
			if item.Name.Local == "name" {
				attributeName = "path"
			}
			value := "."
			for _, attribute := range item.Attr {
				if attribute.Name.Local == attributeName {
					value = attribute.Value
				}
			}
			if item.Name.Local == "name" {
				value = "name(" + value + ")"
			}
			parts = append(parts, messagePartXML{Expression: true, Value: value})
			if err := decoder.Skip(); err != nil {
				return nil, err
			}
		case xml.EndElement:
			if item.Name == start.Name {
				return parts, nil
			}
		}
	}
}

type ruleXML struct {
	Context string     `xml:"context,attr"`
	Lets    []letXML   `xml:"let"`
	Asserts []checkXML `xml:"assert"`
	Reports []checkXML `xml:"report"`
}

type patternXML struct {
	ID    string    `xml:"id,attr"`
	Rules []ruleXML `xml:"rule"`
}

type diagnosticsXML struct {
	Items []diagnosticXML `xml:"diagnostic"`
}

type schemaXML struct {
	DefaultPhase string         `xml:"defaultPhase,attr"`
	Namespaces   []namespaceXML `xml:"ns"`
	Phases       []phaseXML     `xml:"phase"`
	Patterns     []patternXML   `xml:"pattern"`
	Diagnostics  diagnosticsXML `xml:"diagnostics"`
}

type compiledPart struct {
	text       string
	expression *xpath3.Expression
}

type compiledCheck struct {
	kind        string
	id          string
	role        string
	flag        string
	testSource  string
	test        *xpath3.Expression
	diagnostics []string
	message     []compiledPart
}

type compiledLet struct {
	name  string
	value *xpath3.Expression
}

type compiledRule struct {
	contextSource string
	context       *xpath3.Expression
	lets          []compiledLet
	checks        []compiledCheck
}

type compiledPattern struct {
	id    string
	rules []compiledRule
}

// Schema is a reusable compiled Schematron schema.
type Schema struct {
	name            string
	phase           string
	namespaces      map[string]string
	active          map[string]bool
	patterns        []compiledPattern
	diagnostics     map[string][]compiledPart
	diagnosticOrder []string
}

func compileExpression(compiler xpath3.Compiler, namespaces map[string]string, source string) (*xpath3.Expression, error) {
	expression, err := compiler.Compile(source)
	if err != nil {
		return nil, fmt.Errorf("XPATH_PARSE_ERROR expression=%q: %w", source, err)
	}
	if err := expression.Validate(namespaces); err != nil {
		return nil, fmt.Errorf("XPATH_STATIC_ERROR expression=%q: %w", source, err)
	}
	return expression, nil
}

func compileMessage(compiler xpath3.Compiler, namespaces map[string]string, input []messagePartXML) ([]compiledPart, error) {
	parts := make([]compiledPart, 0, len(input))
	for _, part := range input {
		if !part.Expression {
			parts = append(parts, compiledPart{text: part.Value})
			continue
		}
		expression, err := compileExpression(compiler, namespaces, part.Value)
		if err != nil {
			return nil, err
		}
		parts = append(parts, compiledPart{expression: expression})
	}
	return parts, nil
}

// CompileSchema parses and compiles an original libSBGN Schematron file.
func CompileSchema(schemaPath, requestedPhase string) (*Schema, error) {
	data, err := os.ReadFile(schemaPath)
	if err != nil {
		return nil, fmt.Errorf("SCHEMATRON_PARSE_ERROR: %w", err)
	}
	return CompileSchemaBytes(filepath.Base(schemaPath), data, requestedPhase)
}

// CompileSchemaBytes compiles Schematron from an in-memory rule source.
func CompileSchemaBytes(schemaName string, data []byte, requestedPhase string) (*Schema, error) {
	return compileSchemaBytes(schemaName, data, requestedPhase, Strict03, sbgnML03)
}

func compileSchemaBytes(
	schemaName string,
	data []byte,
	requestedPhase string,
	policy NamespacePolicy,
	effectiveNamespace string,
) (*Schema, error) {
	var raw schemaXML
	if err := xml.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("SCHEMATRON_PARSE_ERROR: %w", err)
	}
	phase := requestedPhase
	if policy == AllowSBGNML02 && phase == "basic" {
		for _, candidate := range raw.Phases {
			if candidate.ID == compatibilityPhase {
				phase = compatibilityPhase
				break
			}
		}
	}
	if phase == "" {
		phase = raw.DefaultPhase
	}
	if phase == "" {
		phase = "#ALL"
	}
	namespaces := make(map[string]string, len(raw.Namespaces))
	sbgnBindingCount := 0
	for _, namespace := range raw.Namespaces {
		if namespace.Prefix == "sbgn" {
			sbgnBindingCount++
			if effectiveNamespace == sbgnML02 {
				if namespace.URI != sbgnML03 && namespace.URI != sbgnML02 {
					return nil, fmt.Errorf(
						"SCHEMATRON_NAMESPACE_ERROR: unsafe sbgn binding %s", namespace.URI,
					)
				}
				namespace.URI = sbgnML02
			}
		}
		namespaces[namespace.Prefix] = namespace.URI
	}
	if effectiveNamespace == sbgnML02 && sbgnBindingCount != 1 {
		return nil, fmt.Errorf(
			"SCHEMATRON_NAMESPACE_ERROR: expected one sbgn namespace binding",
		)
	}
	active := make(map[string]bool)
	foundPhase := phase == "#ALL"
	for _, candidate := range raw.Phases {
		if candidate.ID == phase {
			foundPhase = true
			for _, item := range candidate.Active {
				active[item.Pattern] = true
			}
		}
	}
	if !foundPhase {
		return nil, fmt.Errorf("PHASE_NOT_FOUND: %s", phase)
	}

	compiler := xpath3.NewCompiler()
	schema := &Schema{
		name: schemaName, phase: phase, namespaces: namespaces,
		active: active, diagnostics: make(map[string][]compiledPart),
	}
	for _, rawDiagnostic := range raw.Diagnostics.Items {
		message, err := compileMessage(compiler, namespaces, rawDiagnostic.Message)
		if err != nil {
			return nil, fmt.Errorf("diagnostic %s: %w", rawDiagnostic.ID, err)
		}
		schema.diagnostics[rawDiagnostic.ID] = message
		schema.diagnosticOrder = append(schema.diagnosticOrder, rawDiagnostic.ID)
	}
	for _, rawPattern := range raw.Patterns {
		pattern := compiledPattern{id: rawPattern.ID}
		for _, rawRule := range rawPattern.Rules {
			selector := rawRule.Context
			if !strings.HasPrefix(selector, "/") {
				selector = "//" + selector
			}
			contextExpression, err := compileExpression(compiler, namespaces, selector)
			if err != nil {
				return nil, fmt.Errorf("rule context %q: %w", rawRule.Context, err)
			}
			rule := compiledRule{contextSource: rawRule.Context, context: contextExpression}
			for _, rawLet := range rawRule.Lets {
				expression, err := compileExpression(compiler, namespaces, rawLet.Value)
				if err != nil {
					return nil, fmt.Errorf("let $%s: %w", rawLet.Name, err)
				}
				rule.lets = append(rule.lets, compiledLet{name: rawLet.Name, value: expression})
			}
			checks := []struct {
				kind string
				item checkXML
			}{}
			for _, item := range rawRule.Asserts {
				checks = append(checks, struct {
					kind string
					item checkXML
				}{"assert", item})
			}
			for _, item := range rawRule.Reports {
				checks = append(checks, struct {
					kind string
					item checkXML
				}{"report", item})
			}
			for _, rawCheck := range checks {
				test, err := compileExpression(compiler, namespaces, rawCheck.item.Test)
				if err != nil {
					return nil, fmt.Errorf("rule %s: %w", rawCheck.item.ID, err)
				}
				message, err := compileMessage(compiler, namespaces, rawCheck.item.Message)
				if err != nil {
					return nil, fmt.Errorf("rule %s message: %w", rawCheck.item.ID, err)
				}
				rule.checks = append(rule.checks, compiledCheck{
					kind: rawCheck.kind, id: rawCheck.item.ID, role: rawCheck.item.Role,
					flag: rawCheck.item.Flag, testSource: rawCheck.item.Test, test: test,
					diagnostics: rawCheck.item.Diagnostics, message: message,
				})
			}
			pattern.rules = append(pattern.rules, rule)
		}
		schema.patterns = append(schema.patterns, pattern)
	}
	return schema, nil
}

// CompileBuiltin detects the SBGN language and compiles its embedded rules.
func CompileBuiltin(documentPath, phase string) (*Schema, error) {
	return CompileBuiltinWithPolicy(documentPath, phase, Strict03)
}

// CompileBuiltinWithPolicy selects embedded rules using an explicit namespace policy.
func CompileBuiltinWithPolicy(
	documentPath, phase string,
	policy NamespacePolicy,
) (*Schema, error) {
	language, documentNamespace, err := InspectDocument(documentPath)
	if err != nil {
		return nil, err
	}
	effectiveNamespace, err := policy.effectiveNamespace(documentNamespace)
	if err != nil {
		return nil, err
	}
	name, data, err := rules.Load(language)
	if err != nil {
		return nil, err
	}
	return compileSchemaBytes(name, data, phase, policy, effectiveNamespace)
}

// DetectLanguage reads the language attribute from the first SBGN map element.
func DetectLanguage(documentPath string) (string, error) {
	language, _, err := InspectDocument(documentPath)
	return language, err
}

// InspectDocument reads the root namespace and first map language.
func InspectDocument(documentPath string) (string, string, error) {
	file, err := os.Open(documentPath)
	if err != nil {
		return "", "", fmt.Errorf("XML_PARSE_ERROR: %w", err)
	}
	defer file.Close()
	decoder := xml.NewDecoder(file)
	var documentNamespace string
	rootSeen := false
	for {
		token, err := decoder.Token()
		if err != nil {
			return "", "", fmt.Errorf(
				"SCHEMATRON_SCHEMA_ERROR: SBGN map language is missing: %w", err,
			)
		}
		start, ok := token.(xml.StartElement)
		if !ok {
			continue
		}
		if !rootSeen {
			rootSeen = true
			if start.Name.Local != "sbgn" {
				return "", "", fmt.Errorf("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing")
			}
			documentNamespace = start.Name.Space
			continue
		}
		if start.Name.Local == "map" && start.Name.Space == documentNamespace {
			for _, attribute := range start.Attr {
				if attribute.Name.Local == "language" && attribute.Value != "" {
					return attribute.Value, documentNamespace, nil
				}
			}
			return "", "", fmt.Errorf("SCHEMATRON_SCHEMA_ERROR: SBGN map language is missing")
		}
	}
}

// CompileSchemaForDocument compiles an explicit schema for one document policy.
func CompileSchemaForDocument(
	schemaPath, documentPath, phase string,
	policy NamespacePolicy,
) (*Schema, error) {
	_, documentNamespace, err := InspectDocument(documentPath)
	if err != nil {
		return nil, err
	}
	effectiveNamespace, err := policy.effectiveNamespace(documentNamespace)
	if err != nil {
		return nil, err
	}
	data, err := os.ReadFile(schemaPath)
	if err != nil {
		return nil, fmt.Errorf("SCHEMATRON_PARSE_ERROR: %w", err)
	}
	return compileSchemaBytes(
		filepath.Base(schemaPath), data, phase, policy, effectiveNamespace,
	)
}

type currentFunction struct{ node helium.Node }

func (function currentFunction) MinArity() int { return 0 }
func (function currentFunction) MaxArity() int { return 0 }
func (function currentFunction) Call(_ context.Context, _ []xpath3.Sequence) (xpath3.Sequence, error) {
	return xpath3.SingleNode(function.node), nil
}

func pointer(value string) *string {
	if value == "" {
		return nil
	}
	copy := value
	return &copy
}

func evaluator(schema *Schema, variables map[string]xpath3.Sequence, current helium.Node) xpath3.Evaluator {
	return xpath3.NewEvaluator(xpath3.DefaultEvaluatorOptions).
		Namespaces(schema.namespaces).
		Variables(variables).
		Functions(map[string]xpath3.Function{"current": currentFunction{node: current}}, nil)
}

func render(parts []compiledPart, eval xpath3.Evaluator, node helium.Node) (string, error) {
	var output strings.Builder
	for _, part := range parts {
		if part.expression == nil {
			output.WriteString(part.text)
			continue
		}
		result, err := eval.Evaluate(context.Background(), part.expression, node)
		if err != nil {
			return "", err
		}
		output.WriteString(result.Copy().StringValue())
	}
	value := strings.Join(strings.Fields(output.String()), " ")
	return clockPattern.ReplaceAllString(value, "<CURRENT_TIME>"), nil
}

func elementIdentity(node helium.Node) (string, string) {
	element, ok := helium.AsNode[*helium.Element](node)
	if !ok {
		return "", node.Name()
	}
	id, _ := element.GetAttribute("id")
	return id, element.LocalName()
}

func location(node helium.Node) string {
	if node == nil || node.Type() == helium.DocumentNode {
		return ""
	}
	position := 1
	for sibling := node.PrevSibling(); sibling != nil; sibling = sibling.PrevSibling() {
		if sibling.Type() == helium.ElementNode && sibling.Name() == node.Name() {
			position++
		}
	}
	return fmt.Sprintf("%s/%s[%d]", location(node.Parent()), node.Name(), position)
}

// Validate parses and validates one document using the compiled schema.
func (schema *Schema) Validate(ctx context.Context, documentPath string) (Report, error) {
	data, err := os.ReadFile(documentPath)
	if err != nil {
		return Report{}, fmt.Errorf("XML_PARSE_ERROR: %w", err)
	}
	document, err := helium.NewParser().BlockXXE(true).Parse(ctx, data)
	if err != nil {
		return Report{}, fmt.Errorf("XML_PARSE_ERROR: %w", err)
	}
	findings := make([]Finding, 0)
	for _, pattern := range schema.patterns {
		if schema.phase != "#ALL" && !schema.active[pattern.id] {
			continue
		}
		for _, rule := range pattern.rules {
			matched, err := evaluator(schema, nil, document).Evaluate(ctx, rule.context, document)
			if err != nil {
				return Report{}, fmt.Errorf("XPATH_DYNAMIC_ERROR context=%q: %w", rule.contextSource, err)
			}
			nodes, err := matched.Nodes()
			if err != nil {
				return Report{}, fmt.Errorf("XPATH_DYNAMIC_ERROR context=%q is not nodes: %w", rule.contextSource, err)
			}
			for _, node := range nodes {
				variables := make(map[string]xpath3.Sequence)
				eval := evaluator(schema, variables, node)
				for _, binding := range rule.lets {
					value, err := eval.Evaluate(ctx, binding.value, node)
					if err != nil {
						return Report{}, fmt.Errorf("XPATH_DYNAMIC_ERROR let=$%s: %w", binding.name, err)
					}
					copied := value.Copy()
					variables[binding.name] = copied.Sequence()
					eval = evaluator(schema, variables, node)
				}
				for _, check := range rule.checks {
					result, err := eval.Evaluate(ctx, check.test, node)
					if err != nil {
						return Report{}, fmt.Errorf("XPATH_DYNAMIC_ERROR rule=%s: %w", check.id, err)
					}
					truth, err := xpath3.EBV(result.Sequence())
					if err != nil {
						return Report{}, fmt.Errorf("XPATH_DYNAMIC_ERROR rule=%s boolean: %w", check.id, err)
					}
					fires := (check.kind == "assert" && !truth) || (check.kind == "report" && truth)
					if !fires {
						continue
					}
					message, err := render(check.message, eval, node)
					if err != nil {
						return Report{}, fmt.Errorf("XPATH_DYNAMIC_ERROR rule=%s message: %w", check.id, err)
					}
					diagnosticReferences := make([]DiagnosticReference, 0, len(check.diagnostics))
					var diagnosticElementID string
					selectedDiagnostics := make(map[string]bool, len(check.diagnostics))
					for _, diagnosticID := range check.diagnostics {
						selectedDiagnostics[diagnosticID] = true
					}
					for _, diagnosticID := range schema.diagnosticOrder {
						if !selectedDiagnostics[diagnosticID] {
							continue
						}
						parts, ok := schema.diagnostics[diagnosticID]
						if !ok {
							return Report{}, fmt.Errorf("SCHEMATRON_SCHEMA_ERROR: unknown diagnostic %s", diagnosticID)
						}
						value, err := render(parts, eval, node)
						if err != nil {
							return Report{}, fmt.Errorf("XPATH_DYNAMIC_ERROR diagnostic=%s: %w", diagnosticID, err)
						}
						diagnosticReferences = append(diagnosticReferences, DiagnosticReference{
							Diagnostic: diagnosticID,
							Text:       value,
						})
						if diagnosticID == "id" && diagnosticElementID == "" {
							diagnosticElementID = value
						}
					}
					elementID, elementKind := elementIdentity(node)
					if diagnosticElementID != "" {
						elementID = diagnosticElementID
					}
					findingType := "failed-assert"
					if check.kind == "report" {
						findingType = "successful-report"
					}
					findings = append(findings, Finding{
						ID: pointer(check.id), Type: findingType, Role: pointer(check.role),
						Flag: pointer(check.flag), Location: location(node),
						Test: strings.Join(strings.Fields(check.testSource), " "),
						Text: message, DiagnosticReferences: diagnosticReferences,
						Derived: DerivedIdentity{
							ElementID: pointer(elementID), ElementKind: elementKind,
						},
					})
				}
			}
		}
	}
	sort.Slice(findings, func(left, right int) bool {
		leftRule, rightRule := "", ""
		if findings[left].ID != nil {
			leftRule = *findings[left].ID
		}
		if findings[right].ID != nil {
			rightRule = *findings[right].ID
		}
		if leftRule != rightRule {
			return leftRule < rightRule
		}
		leftElement, rightElement := "", ""
		if findings[left].Derived.ElementID != nil {
			leftElement = *findings[left].Derived.ElementID
		}
		if findings[right].Derived.ElementID != nil {
			rightElement = *findings[right].Derived.ElementID
		}
		if leftElement != rightElement {
			return leftElement < rightElement
		}
		if findings[left].Location != findings[right].Location {
			return findings[left].Location < findings[right].Location
		}
		return findings[left].Text < findings[right].Text
	})
	return Report{
		Schema: schema.name, Phase: schema.phase, Valid: len(findings) == 0, Findings: findings,
		Backend: &BackendInfo{
			Language: "go", Implementation: "sbgn-validator-go",
			ImplementationVersion: "0.1.1", SchematronEngine: "project-direct-interpreter",
			XPathEngine: "helium/xpath3", XPathVersion: "3.1",
			ProfileVersion: profileVersion, NativeSchematron: true,
		},
	}, nil
}

// IsValidationError reports whether an error belongs to the stable validator taxonomy.
func IsValidationError(err error) bool {
	return err != nil && !errors.Is(err, context.Canceled)
}
