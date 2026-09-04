package sbgnvalidator

import (
	"context"
	"path/filepath"
	"testing"
)

func TestValidateUsesBuiltInRules(t *testing.T) {
	document := filepath.Join("..", "tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn")
	report, err := Validate(context.Background(), document, "basic")
	if err != nil {
		t.Fatal(err)
	}
	if report.Schema != "sbgn_pd.sch" || report.Valid {
		t.Fatalf("unexpected report: %#v", report)
	}
	canonical, err := ValidateWithRules(
		context.Background(), document, filepath.Join("..", "validation/rules/sbgn_pd.sch"), "basic",
	)
	if err != nil {
		t.Fatal(err)
	}
	if len(report.Findings) != len(canonical.Findings) {
		t.Fatal("built-in and canonical rules returned different findings")
	}
	info, err := RulesInfo()
	if err != nil {
		t.Fatal(err)
	}
	if info.RulesetDigest == "" {
		t.Fatal("built-in rules digest is missing")
	}
}
