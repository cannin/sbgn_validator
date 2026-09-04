APPNAME := sbgn-validator

.PHONY: all test release current clean
all: test release current

test:
	gofmt -w ./cmd ./internal
	go test ./...

release: clean
	mkdir -p dist
	GOOS=linux GOARCH=amd64 go build -o dist/$(APPNAME)-linux-amd64 ./cmd/validator
	GOOS=linux GOARCH=arm64 go build -o dist/$(APPNAME)-linux-arm64 ./cmd/validator
	GOOS=darwin GOARCH=amd64 go build -o dist/$(APPNAME)-darwin-amd64 ./cmd/validator
	GOOS=darwin GOARCH=arm64 go build -o dist/$(APPNAME)-darwin-arm64 ./cmd/validator
	GOOS=windows GOARCH=amd64 go build -o dist/$(APPNAME)-windows-amd64.exe ./cmd/validator
	GOOS=windows GOARCH=arm64 go build -o dist/$(APPNAME)-windows-arm64.exe ./cmd/validator

current:
	mkdir -p dist
	go build -o dist/$(APPNAME) ./cmd/validator

clean:
	rm -rf dist
