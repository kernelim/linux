MAKEFLAGS := --no-print-directory

.PHONY: all
all:
	@awk -f scripts/check-multiple-entries.awk info/owners.yaml
	@$(MAKE) -C scripts fullbuild
	scripts/yaml2RHMAINTAINERS info/owners.yaml > info/RHMAINTAINERS
	scripts/yaml2CODEOWNERS info/owners.yaml > info/CODEOWNERS
	scripts/verifySubsystems info/owners.yaml
	scripts/checks.sh

clean:
	@$(MAKE) -C scripts clean
