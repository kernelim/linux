# CentOS Documentation

- [https://gitlab.com/redhat/centos-stream/src/kernel/documentation](https://gitlab.com/redhat/centos-stream/src/kernel/documentation)
- [https://redhat.gitlab.io/centos-stream/src/kernel/documentation/](https://redhat.gitlab.io/centos-stream/src/kernel/documentation/)

The `rhdocs/` git-subtree has been effectively replaced by this file.

Please visit the centos-stream documentation project linked above.

## A quick PSA

If you would like to replicate the previous "structure" of the rhdocs directory
within the CentOS docs repo, clone the docs project.
```bash
git clone https://gitlab.com/redhat/centos-stream/src/kernel/documentation.git ~/
ln -sfn ~/documentation/ ./rhdocs/

pushd ~/documentation && make info/RHMAINTAINERS
```
Then add the following to a `.get_maintainer.conf` file in the root of the
repository.

`--mpath redhat/rhdocs/info/RHMAINTAINERS --no-git --no-git-fallback`

