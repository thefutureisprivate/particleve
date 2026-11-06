# Source-change webhooks

The owner chose to register these webhooks. No new service token has been created
by the implementation. Dependency rebuilds use OBS's transitive repository graph;
source pushes need the following four package-scoped hooks.

For each package below, create a token limited to that package (default operation:
runservice), using your own authenticated osc session:

```sh
osc token --create home:thefutureisprivate:particleve particleve-image
osc token --create home:thefutureisprivate:particleve particleve-integration
osc token --create home:thefutureisprivate:particleve mkosi
osc token --create home:thefutureisprivate:particleve fwupd-efi
```

Each response contains a numerical ID and a secret. In
[the ParticleVE repository webhook settings](https://github.com/thefutureisprivate/particleve/settings/hooks),
create one hook per token:

- Payload URL: `https://api.opensuse.org/trigger/webhook?id=NUMERICAL_ID`.
- Secret: that token's secret, entered only in GitHub's secret field.
- Content type: `application/json`; SSL verification enabled.
- Events: pushes only; hook active.

Do not put a token secret in a URL, Git, source-service definition or image. No
GitHub personal access token, commit-status write permission or wildcard OBS token
is required for these source-service hooks. All four services fetch the configured
public repository's `main` branch. Pushes to other branches leave those inputs
unchanged; obs_scm skips unchanged source results.

After registering, push a harmless tracked documentation change to main and check
GitHub's delivery history and the OBS service results. Confirm the generated
`particleve.obsinfo` reports the expected commit and a new complete numeric image
version appears only after all build/signature checks pass. Record this source
rebuild and a separate dependency-only rebuild in commissioning evidence. Keep
actual build outcomes distinct from successful webhook delivery.

This follows the official [OBS source-service webhook guide](https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-source-services#sec-obs-source-services-webhook)
and [package-scoped token authorization](https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-authorization-token).
