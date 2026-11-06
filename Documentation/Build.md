# Build and publication

This checkout is the ParticleOS fork. Build it directly; no overlay composition
or second ParticleOS download is required. `sources.lock.json` pins the upstream
base, unmodified mkosi and fwupd-efi. Fedora 45 and the upstream stable systemd
repository apply to runtime, initrd and build tools. Installed RPM origins and
family versions are checked during the build, rather than inferred from names.

`obs/site.json` contains the owned project, source branch, package repository and
single image feed. `tools/configure-build.py` validates public trust and generates
tracked repository and image inputs. It never imports private keys. Local builds
use normal mkosi signing options with private keys outside this checkout. OBS
builds automatically select mkosi's native deferred-signing integration.

```sh
make sources
PYTHONPATH=. python3 tools/configure-build.py --site obs/site.json
make summary
PYTHONPATH=. python3 tools/obs-project.py --site obs/site.json --summary build/summary.json
```

The generated `.obs/fedora/x86-64/mkosi.conf` schedules dependencies from all three
resolved trees. OBS builds the checkout's root `mkosi.conf`, supplies the advancing
`CI_CNT.B_CNT` image version, and rebuilds on transitive dependency changes.
`packaging/` supplies the pinned mkosi, integration/build hooks and separately
PE-signed fwupd helper. The helper's one documented patch changes a successful
SBOM linker-selection message from warning to informational; compiler warnings
remain fatal, and SBOM/SBAT sections are checked.

After the native signing stages attach verity, PCR and PE signatures, the final
hook verifies the root hash, partition payloads, UKI identity/security policy,
bootloader, fwupd helper and project certificate. It emits a versioned release
manifest alongside the six required artifacts. OBS signs its native `SHA256SUMS`
index, covering the manifest and final artifact bytes. Clients authenticate that
index and the complete manifest before any disk write. There is no deployment
or promotion service. Interrupted/incomplete signing stages emit no release
manifest and therefore cannot become eligible releases.

Public signing identities:

- GPG fingerprint: `411E78DB29ECC8276328B3F526F1183EEA4C1F07`.
- EFI certificate SHA256:
  `7B:98:38:86:2B:14:3E:F0:69:E2:B2:70:0B:39:6B:9D:77:60:F0:16:F0:10:24:E3:0A:CD:8C:81:44:B0:6D:12`.
- Stable-systemd package GPG fingerprint:
  `CF496DFD918C8A3F55C56EBC713BF72732820778`.

These public files are in `mkosi.extra/usr/lib/particleve/trust/`. Enroll the
intended EFI certificate through owner-controlled firmware procedures. A future
rotation requires an explicitly reviewed overlap, signed releases trusted by the
installed key, both independent boot paths and TPM recovery testing; no implicit
trust migration is implemented.

The source repository is `https://github.com/thefutureisprivate/particleve`, branch
`main`. `.obs/workflows.yml` describes source-service triggers. Source refresh
must be wired to the owned repository once publishing access is available; that
webhook has not yet been established. Dependency rebuilds already use OBS's
native repository graph. No permanent external runner is required.

`tools/obs-upload.py` commits reviewed source directories atomically. Its
credential file is two lines (OBS username/password), mode 0600; credentials are
sent only to `api.opensuse.org`, redirects are refused, and no credential is
written to sources. Do not add `/tmp/obs-pw` or any private key to Git or uploads.
