package validator

import (
	"context"
	"fmt"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func repositoryRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate test source")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "../../.."))
}

func TestLegacyPolicyRunsSemanticRules(t *testing.T) {
	root := repositoryRoot(t)
	schema, err := CompileSchema(filepath.Join(root, "validation/rules/sbgn_pd.sch"), "basic")
	if err != nil {
		t.Fatal(err)
	}
	document := filepath.Join(root, "tests/examples/go_mf_conflicts.sbgn")
	report, err := schema.Validate(context.Background(), document)
	if err != nil {
		t.Fatal(err)
	}
	if report.Valid || len(report.Findings) != 1 || report.Findings[0].ID == nil ||
		*report.Findings[0].ID != "sbgn-namespace-0.3" {
		t.Fatalf("expected namespace Schematron finding, got %#v", report.Findings)
	}
	override, err := CompileSchemaForDocument(
		filepath.Join(root, "validation/rules/sbgn_pd.sch"), document, "basic",
		AllowSBGNML02,
	)
	if err != nil {
		t.Fatal(err)
	}
	report, err = override.Validate(context.Background(), document)
	if err != nil {
		t.Fatal(err)
	}
	if report.Valid {
		t.Fatal("expected legacy semantic failures")
	}
	found := make(map[string]bool)
	for _, finding := range report.Findings {
		if finding.ID != nil {
			found[*finding.ID] = true
		}
	}
	for _, ruleID := range []string{"pd10102", "pd10132", "pd10141"} {
		if !found[ruleID] {
			t.Fatalf("expected %s finding, got %#v", ruleID, report.Findings)
		}
	}
}

func TestNamespacePolicyRejectsUnsupportedNamespaces(t *testing.T) {
	root := repositoryRoot(t)
	for _, relative := range []string{
		"tests/examples/go_mf_conflicts.sbgn",
		"tests/fixtures/compatibility/missing-namespace.sbgn",
		"tests/fixtures/compatibility/unrelated-namespace.sbgn",
		"tests/fixtures/compatibility/future-namespace.sbgn",
	} {
		_, err := CompileBuiltinWithPolicy(filepath.Join(root, relative), "basic", Strict03)
		if err == nil || !strings.HasPrefix(err.Error(), "SBGN_NAMESPACE_ERROR:") {
			t.Fatalf("expected strict namespace error for %s, got %v", relative, err)
		}
		if relative != "tests/examples/go_mf_conflicts.sbgn" {
			_, err = CompileBuiltinWithPolicy(filepath.Join(root, relative), "basic", AllowSBGNML02)
			if err == nil || !strings.HasPrefix(err.Error(), "SBGN_NAMESPACE_ERROR:") {
				t.Fatalf("expected compatibility namespace error for %s, got %v", relative, err)
			}
		}
	}
}

func TestLegacyPolicySupportsAllLanguagesAndCustomRules(t *testing.T) {
	root := repositoryRoot(t)
	cases := map[string]string{
		"af": "tests/fixtures/compatibility/sbgnml-0.2-af-valid.sbgn",
		"er": "tests/fixtures/compatibility/sbgnml-0.2-er-valid.sbgn",
		"pd": "tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn",
	}
	for language, relative := range cases {
		document := filepath.Join(root, relative)
		builtin, err := CompileBuiltinWithPolicy(document, "basic", AllowSBGNML02)
		if err != nil {
			t.Fatal(err)
		}
		custom, err := CompileSchemaForDocument(
			filepath.Join(root, "validation/rules/sbgn_"+language+".sch"),
			document,
			"basic",
			AllowSBGNML02,
		)
		if err != nil {
			t.Fatal(err)
		}
		for _, schema := range []*Schema{builtin, custom} {
			report, err := schema.Validate(context.Background(), document)
			if err != nil || !report.Valid {
				t.Fatalf("expected valid %s compatibility report: %#v, %v", language, report, err)
			}
		}
	}
}

func TestCustomSchemaRebindsOnlySBGNPrefix(t *testing.T) {
	root := repositoryRoot(t)
	document := filepath.Join(root, "tests/fixtures/compatibility/custom-sbgnml-0.2.sbgn")
	schema, err := CompileSchemaForDocument(
		filepath.Join(root, "tests/fixtures/compatibility/custom-sbgn.sch"),
		document,
		"basic",
		AllowSBGNML02,
	)
	if err != nil {
		t.Fatal(err)
	}
	report, err := schema.Validate(context.Background(), document)
	if err != nil || !report.Valid {
		t.Fatalf("expected custom compatibility schema to pass: %#v, %v", report, err)
	}
	_, err = CompileSchemaForDocument(
		filepath.Join(root, "tests/fixtures/compatibility/custom-unsafe-sbgn.sch"),
		document,
		"basic",
		AllowSBGNML02,
	)
	if err == nil || !strings.HasPrefix(err.Error(), "SCHEMATRON_NAMESPACE_ERROR:") {
		t.Fatalf("expected unsafe custom binding error, got %v", err)
	}
}

func TestNamespacePolicyHasNoSequentialOrConcurrentContamination(t *testing.T) {
	root := repositoryRoot(t)
	documents := []string{
		filepath.Join(root, "tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn"),
		filepath.Join(root, "tests/fixtures/error-test-files/PD/pd10110-pass.sbgn"),
	}
	validate := func(t *testing.T, document string) {
		t.Helper()
		schema, err := CompileBuiltinWithPolicy(document, "basic", AllowSBGNML02)
		if err != nil {
			t.Fatal(err)
		}
		report, err := schema.Validate(context.Background(), document)
		if err != nil || !report.Valid {
			t.Fatalf("expected valid compatibility report: %#v, %v", report, err)
		}
	}
	for index := 0; index < 4; index++ {
		validate(t, documents[index%len(documents)])
	}
	for index, document := range documents {
		t.Run(fmt.Sprintf("parallel-%d", index), func(t *testing.T) {
			t.Parallel()
			validate(t, document)
		})
	}
}

func TestPDReferenceFixture(t *testing.T) {
	root := repositoryRoot(t)
	schema, err := CompileSchema(filepath.Join(root, "validation/rules/sbgn_pd.sch"), "basic")
	if err != nil {
		t.Fatal(err)
	}
	report, err := schema.Validate(context.Background(), filepath.Join(
		root, "tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn",
	))
	if err != nil {
		t.Fatal(err)
	}
	for _, finding := range report.Findings {
		if finding.ID != nil && *finding.ID == "pd10110" {
			return
		}
	}
	t.Fatal("expected pd10110 finding")
}

func TestBuiltinRulesDetectLanguage(t *testing.T) {
	root := repositoryRoot(t)
	document := filepath.Join(root, "tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn")
	schema, err := CompileBuiltin(document, "basic")
	if err != nil {
		t.Fatal(err)
	}
	report, err := schema.Validate(context.Background(), document)
	if err != nil {
		t.Fatal(err)
	}
	if report.Schema != "sbgn_pd.sch" {
		t.Fatalf("unexpected built-in schema: %s", report.Schema)
	}
}
