MAKEFLAGS := --no-print-directory

.PHONY: all
all:
	@awk -f scripts/check-multiple-entries.awk info/owners.yaml
	@$(MAKE) -C scripts fullbuild
	scripts/yaml2RHMAINTAINERS info/owners.yaml > info/RHMAINTAINERS
	scripts/yaml2CODEOWNERS info/owners.yaml > info/CODEOWNERS
	scripts/verifySubsystems info/owners.yaml
	@if test -n "$$(git diff --name-status main | grep owners.yaml)" && \
		test "$$(git-config --get owners.warning)" != "false"; then \
		echo "======================================================="; \
		echo "These changes include owners.yaml modifications.  Please"; \
		echo "review these Merge Request Approval Rules.  The Merge Request"; \
		echo "author must add the appropriate engineers as reviewers on"; \
		echo "the submitted documentation project Merge Request."; \
		echo " "; \
		echo "* Included and excluded file changes can be merged if the"; \
		echo "MR author is a subsystem maintainer. If the author is not a"; \
		echo "subsystem maintainer, then the subsystem maintainer must"; \
		echo "provide an approve."; \
		echo " "; \
		echo "* Any MR adding an engineer in a role must be authored by"; \
		echo "or approved by the added engineer. An additional approve from a"; \
		echo "subsystem maintainer is required, unless the maintainer is the"; \
		echo "author of the MR."; \
		echo " "; \
		echo "* Any MR removing an engineer in a role must be authored by"; \
		echo "or approved by the removed engineer, except in the case when"; \
		echo "the removed engineer is no longer with Red Hat. While removals"; \
		echo "from roles do not require the approve of the maintainer, MR"; \
		echo "authors are encouraged to add the maintainer for an approve."; \
		echo " "; \
		echo "This warning can be disabled by executing:"; \
		echo "        git-config --add owners.warning false"; \
		echo "======================================================="; \
	fi
clean:
	@$(MAKE) -C scripts clean
