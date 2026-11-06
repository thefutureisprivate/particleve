Name:           particleve-integration
Version:        0.1.0
Release:        1%{?dist}
Summary:        ParticleVE host installation and maintenance coordinator
License:        LGPL-2.1-or-later
Source0:        particleve-integration-%{version}.tar.xz
BuildArch:      noarch
BuildRequires:  python3 >= 3.14
BuildRequires:  gnupg2
BuildRequires:  coreutils
Requires:       python3 >= 3.14
Requires:       systemd-udev
Requires:       systemd-container
Requires:       mdadm
Requires:       cryptsetup
Requires:       btrfs-progs
Requires:       gnupg2
Requires:       sbsigntools
Requires:       systemd-ukify

%package -n particleve-build-tools
Summary:        ParticleVE verification hooks for native OBS image signing
Requires:       python3 >= 3.14
Requires:       rpm
Requires:       sbsigntools
Requires:       openssl
Requires:       erofs-utils
Requires:       dosfstools
Requires:       mtools
Requires:       veritysetup
Requires:       systemd-repart
Requires:       systemd-ukify
Requires:       pesign
Requires:       nss-tools
Requires:       cpio
Requires:       jq
Requires:       efitools
Requires:       tar
Requires:       zstd
Requires:       findutils
Requires:       coreutils

%description -n particleve-build-tools
Final artifact verification and metadata assembly within mkosi's native OBS
signing stages. Private signing material stays in OBS.

%description
Explicit-target installation, two-disk OS update transactions and supervised
firmware-maintenance inhibition for the ParticleVE ParticleOS profile.

%prep
%autosetup

%check
python3 -W error -m unittest discover -v

%install
install -d %{buildroot}%{_prefix}/lib/particleve/particleve
install -m0644 particleve/*.py %{buildroot}%{_prefix}/lib/particleve/particleve/
install -d %{buildroot}%{_prefix}/lib/particleve/trust
install -m0644 mkosi.extra/usr/lib/particleve/trust/* %{buildroot}%{_prefix}/lib/particleve/trust/
install -D -m0755 bin/particleve %{buildroot}%{_bindir}/particleve
install -D -m0755 bin/particleve-homed-account %{buildroot}%{_libexecdir}/particleve-homed-account
install -d %{buildroot}%{_prefix}/lib/particleve-build/particleve
install -m0644 particleve/__init__.py particleve/common.py particleve/config.py particleve/release.py \
    particleve/kernels.py particleve/buildartifacts.py %{buildroot}%{_prefix}/lib/particleve-build/particleve/
install -D -m0755 tools/obs-postoutput %{buildroot}%{_libexecdir}/particleve-obs-postoutput

%files
%license LICENSE
%{_bindir}/particleve
%{_libexecdir}/particleve-homed-account
%{_prefix}/lib/particleve/particleve
%{_prefix}/lib/particleve/trust

%files -n particleve-build-tools
%license LICENSE
%{_prefix}/lib/particleve-build
%{_libexecdir}/particleve-obs-postoutput

%changelog
* Fri Nov 06 2026 ParticleVE maintainers <thefutureisprivate@users.noreply.github.com> - 0.1.0-1
- Add homed SSH policy, native Btrfs installation and coordinated vmspawn maintenance.
- Verify final artifacts in the native OBS signing pipeline.
