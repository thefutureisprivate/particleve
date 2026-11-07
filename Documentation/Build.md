# Build and publication

This checkout is the ParticleOS fork. Build it directly; no overlay composition
or second ParticleOS download is required. `sources.lock.json` pins the upstream
base, mkosi revision and fwupd-efi. Fedora 45 and the upstream stable systemd
repository apply to runtime, initrd and build tools. Installed RPM origins and
family versions are checked during the build, rather than inferred from names.
The integration and build-tools RPMs also carry an implementation-content identity
and hashes of their installed payloads. The image checkout computes the expected
identity from runtime modules, helpers, policy sources, trust and packaging inputs.
Both RPMs must match before image generation; final signing checks their payloads
again before publishing a manifest. A failed or delayed independent source webhook
therefore cannot publish new implementation inputs with an old coordinator or
signing helper. Documentation-only changes retain the same implementation identity.
The final EROFS payload is also checked for retained boot/storage and Intel/AMD
KVM drivers, including built-in driver metadata, after mkosi's module filtering.
Module selectors use the pinned mkosi's glob syntax; directory selectors end in `/`.

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
PE-signed fwupd helper. The pinned mkosi RPM requires the build-tools subpackage,
so OBS installs the final-verification and native signing tools in its worker;
image `BuildPackages=` alone schedules downloads without installing those tools.
The mkosi patch repairs its native signing continuation: it regenerates stale
split partitions after verity signing, copies each artifact once, and handles
absent optional signature classes without diagnostics or empty signing rounds.
The exact upstream patch application, shell syntax, and file-backed partition
regeneration were checked locally; the full signing path remains an OBS release gate.
The helper's one documented patch changes a successful
SBOM linker-selection message from warning to informational; compiler warnings
remain fatal, and SBOM/SBAT sections are checked.

After the native signing stages attach verity, PCR and PE signatures, the final
hook verifies the root hash, partition payloads, UKI identity/security policy,
bootloader, fwupd helper and project certificate. It emits a versioned release
manifest alongside the six required artifacts. Signature payloads include NUL
padding to exactly 1 MiB; installed signature slots use that same fixed size.
This fully replaces stale contents on slot reuse, as required by the upstream
signature parser. The other OS partitions retain their configured growth margin.
OBS signs its native `SHA256SUMS`
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

The initial PCR authorization certificate uses RSA4096. Capability preflight
checks TPM support for that policy before disk changes; the TPM2 version alone
does not establish RSA4096 support.

These public files are in `mkosi.extra/usr/lib/particleve/trust/`. Enroll the
intended EFI certificate through owner-controlled firmware procedures. A future
rotation requires an explicitly reviewed overlap, signed releases trusted by the
installed key, both independent boot paths and TPM recovery testing; no implicit
trust migration is implemented.

The signed implementation and upstream Git history have been published.
The source repository is `https://github.com/thefutureisprivate/particleve`, branch
`main`. The four `obs/*/_service` definitions track that branch and extract the relevant
recipes. Integration tarballs are created by native OBS source services; pinned
upstream mkosi/fwupd sources are downloaded from their immutable GitHub commit
URLs. Four package-scoped source-service webhooks avoid granting OBS a GitHub
personal access token. All four GitHub registrations were verified by an automatic
refresh to commit
`fd52ed982ddb80f8163aa70dd8f35a7ecb1fdf23`. Dependency rebuilds use OBS's
native repository graph. No permanent external runner is required.

`tools/obs-upload.py` commits reviewed source directories atomically. Its
credential file is two lines (OBS username/password), mode 0600; credentials are
sent only to `api.opensuse.org`, redirects are refused, and no credential is
written to sources. Do not add `/tmp/obs-pw` or any private key to Git or uploads.
