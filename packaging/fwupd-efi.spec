# needssslcertforbuild
# EFI executables have no installed ELF debug source payload.
%global debug_package %{nil}
Name:           fwupd-efi
Version:        1.9
Release:        1%{?dist}
Summary:        ParticleVE-trusted fwupd EFI capsule helper
License:        LGPL-2.1-or-later
URL:            https://github.com/fwupd/fwupd-efi
Source0:        fwupd-efi-%{version}.tar.xz
Patch0:         fwupd-efi-sbom-linker-message.patch
ExclusiveArch:  x86_64
BuildRequires:  gcc
BuildRequires:  binutils
BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  pkgconfig(gnu-efi) >= 3.0.18
BuildRequires:  python3
BuildRequires:  python3-uswid
BuildRequires:  pesign-obs-integration

# Keep Fedora's BRP diagnostics and transformations. Hash the final PE only after
# those transformations; OBS attaches signatures and repackages the RPM off-host.
%global __os_install_post %{expand:%{__os_install_post}}\
    /usr/lib/rpm/brp-suse.d/brp-99-pesign --files '/usr/libexec/fwupd/efi/fwupdx64.efi'\
%{nil}

%description
Unmodified fwupd-efi 1.9 runtime behavior, compiled for the supported architecture
and separately signed through the OBS PE signing integration. The private key
stays with OBS. The .signed name resolves to the signed executable.

%prep
%autosetup -p1

%build
meson setup build --prefix=/usr --libexecdir=libexec --libdir=lib64 \
    --buildtype=release -Dwerror=true \
    -Defi_sbat_distro_id=particleve \
    -Defi_sbat_distro_summary=ParticleVE \
    -Defi_sbat_distro_pkgname=fwupd-efi \
    -Defi_sbat_distro_version=%{version}-%{release} \
    -Defi_sbat_distro_url=https://github.com/thefutureisprivate/particleve
meson compile -C build

%check
# The bundled linker script is required to retain both SBAT and the SBOM.
objdump -h build/efi/fwupdx64.efi | grep -F .sbat
objdump -h build/efi/fwupdx64.efi | grep -F .sbom

%install
DESTDIR=%{buildroot} meson install -C build
ln -s fwupdx64.efi %{buildroot}%{_libexecdir}/fwupd/efi/fwupdx64.efi.signed

%files
%license COPYING
%{_libexecdir}/fwupd/efi/fwupdx64.efi
%{_libexecdir}/fwupd/efi/fwupdx64.efi.signed
%{_libdir}/pkgconfig/fwupd-efi.pc

%changelog
* Fri Nov 06 2026 ParticleVE maintainers - 1.9-1
- Build the pinned helper with separate OBS PE signing, SBAT and SBOM checks.
