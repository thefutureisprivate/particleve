%global upstream_commit a6753e508681aa162cef4e5183f1a728c11c4d78
Name:           mkosi
Version:        28~0.git.a6753e508681
Release:        1%{?dist}
Summary:        Pinned mkosi for the ParticleVE ParticleOS revision
License:        LGPL-2.1-or-later
Source0:        https://github.com/systemd/mkosi/archive/%{upstream_commit}.tar.gz
BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-setuptools-scm
BuildRequires:  python3-build
BuildRequires:  python3-installer
Requires:       python3
Requires:       python3-pefile
Requires:       systemd-container
Requires:       systemd-ukify
Requires:       systemd-boot
Requires:       systemd-repart
Requires:       dnf5
Requires:       distribution-gpg-keys
Requires:       perl-Config-IniFiles
Requires:       bubblewrap
Requires:       erofs-utils
Requires:       cryptsetup

%description
Unmodified upstream mkosi at the exact revision recorded in sources.lock.json.

%prep
%setup -q -n mkosi-%{upstream_commit}

%build
python3 -m build --wheel --no-isolation

%install
python3 -m installer --destdir=%{buildroot} dist/*.whl

%files
%license LICENSES/LGPL-2.1-or-later.txt
%{_bindir}/mkosi*
%{python3_sitelib}/mkosi*

%changelog
* Fri Nov 06 2026 ParticleVE maintainers <thefutureisprivate@users.noreply.github.com> - 28~0.git.a6753e508681-1
- Build the unmodified upstream revision used by the ParticleVE profile.
