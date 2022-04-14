#!/usr/bin/env python3
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Asserts each commit in a merge request is signed-off-by the author of the
# commit.  Exits 1 if signed-off-bys are missing, or if run in an invalid
# context (i.e. not a merge request).
import os
import sys

import gitlab as gitlab_module

LICENSE_DOCS = "https://gitlab.com/cki-project/kernel-ark/-/wikis/Contributor-Guide#licensing"

# Refer to https://docs.gitlab.com/ee/ci/variables/predefined_variables.html for
# environment variables.
gitlab = gitlab_module.Gitlab(
    os.environ["CI_SERVER_URL"], job_token=os.environ["CI_JOB_TOKEN"], timeout=30
)

project_id = os.environ.get("CI_MERGE_REQUEST_PROJECT_ID")
merge_request_iid = os.environ.get("CI_MERGE_REQUEST_IID")
if project_id is None or merge_request_iid is None:
    print("This test is only valid against merge requests.")
    sys.exit(1)

project = gitlab.projects.get(project_id)
mr = project.mergerequests.get(merge_request_iid)

invalid_commits = []
for commit in mr.commits():
    sign_offs = [
        line.strip()
        for line in commit.message.splitlines()
        if line.strip().startswith("Signed-off-by:")
    ]
    required_sign_off = f"Signed-off-by: {commit.author_name} <{commit.author_email}>"
    if required_sign_off not in sign_offs:
        invalid_commits.append((commit, required_sign_off))


if invalid_commits:
    for commit, required_sign_off in invalid_commits:
        print(f"Commit {commit.id} is missing a '{required_sign_off}' tag.")
    print(f"Refer to {LICENSE_DOCS} for details.")
    sys.exit(1)
