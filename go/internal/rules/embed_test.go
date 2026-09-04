package rules

import (
	"crypto/sha256"
	"encoding/hex"
	"testing"
)

func TestAllEmbeddedRulesMatchManifest(t *testing.T) {
	value, err := manifest()
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"sbgn_af.sch", "sbgn_er.sch", "sbgn_pd.sch"} {
		data, readErr := files.ReadFile("data/" + name)
		if readErr != nil {
			t.Fatalf("read embedded %s: %v", name, readErr)
		}
		actual := sha256.Sum256(data)
		if hex.EncodeToString(actual[:]) != value.Files[name].SHA256 {
			t.Fatalf("embedded %s does not match its manifest hash", name)
		}
	}
}
