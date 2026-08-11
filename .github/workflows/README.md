# CI/CD workflows — one-time manual setup

Before `deploy-prod.yml` can run: create a GitHub Environment named `production`
(repo Settings > Environments > New environment), add at least one required reviewer.

Before either deploy workflow can run: register a self-hosted runner with label
`testscope-k8s` on the control-plane EC2 node (repo Settings > Actions > Runners > New self-hosted
runner; run the provided `config.sh`/`run.sh` as a systemd service on that host). While
registering it, also add the `/etc/hosts` entry from Task 31 (`worker_private_ip
dev.testscope.local testscope.local`) — both deploy workflows' smoke tests curl those
hostnames from the control-plane, so without it they can't resolve.

Before either deploy workflow can reach a namespace's pods past `ContainerCreating`: create
the `github-token` Secret in that namespace (`dev` and/or `prod`) — copy
`kubernetes/base/mcp-test-analysis/secret.yaml.example` to `secret.yaml` (gitignored), fill in
a real GitHub PAT, and `kubectl apply -n <namespace> -f secret.yaml`. Nothing in this repo
creates that Secret automatically (see `docs/project-log.md`'s Phase 7 health check entry) —
`mcp-test-analysis`, `mcp-github`, and its `auth-proxy` sidecar all reference it by name and
won't start without it. `worker` also needs its own `worker-secrets` Secret (`anthropic-api-key`
key) in each namespace, same manual-creation situation, not shipped as an example file here —
create it directly instead:

```
kubectl create secret generic worker-secrets --from-literal=anthropic-api-key=<ANTHROPIC_API_KEY> -n <namespace>
```
