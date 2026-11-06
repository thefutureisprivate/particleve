# Source-change webhooks

Four package-scoped OBS runservice tokens have been created and their server-side
bindings verified. The owner registers the corresponding GitHub webhooks. URLs
and matching secrets are in `/tmp/particleve-obs-webhooks.json` (mode 0600); secrets
are never committed or included in build sources. Dependency rebuilds use OBS's transitive repository graph;
source pushes need the following four package-scoped hooks.

The existing token IDs are 13084 (image), 13087 (integration), 13090 (mkosi),
and 13093 (fwupd-efi). Do not create duplicate tokens. For future replacement,
create a token limited to the appropriate package using your authenticated osc session:

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
