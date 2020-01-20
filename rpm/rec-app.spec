%global commit      8121a4fdd251f9ab8785e5fea00ccbe676a771fd
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global date        20200120

%global sysname rec_app
%global uuid    com.github.amikha1lov.%{sysname}

Name:           rec-app
Version:        0
Release:        3.%{date}git%{shortcommit}%{?dist}
Summary:        User friendly Open Source screencaster for Linux written in GTK
BuildArch:      noarch

License:        GPLv3+
URL:            https://github.com/amikha1lov/rec_app
Source0:        %{url}/archive/%{commit}/%{name}-%{version}.%{date}git%{shortcommit}.tar.gz

BuildRequires:  desktop-file-utils
BuildRequires:  intltool
BuildRequires:  libappstream-glib
BuildRequires:  meson >= 0.50.0
BuildRequires:  python3-devel
BuildRequires:  pkgconfig(glib-2.0)
Requires:       gstreamer1-plugins-base
Requires:       gstreamer1-plugins-good
Requires:       hicolor-icon-theme
Requires:       python3-pulsectl
Requires:       slop
#Recommends:     gstreamer1-plugins-ugly

%description
User friendly Open Source screencaster for Linux written in GTK. Using free
GStreamer modules and not depend on FFmpeg.


%prep
%autosetup -n %{sysname}-%{commit} -p1


%build
%meson
%meson_build


%install
%meson_install
#%%find_lang %{uuid}


%check
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/*.xml
desktop-file-validate %{buildroot}%{_datadir}/applications/*.desktop


%files
%license COPYING
%doc README.md
%{_bindir}/%{sysname}
%{_datadir}/applications/*.desktop
%{_datadir}/glib-2.0/schemas/*.gschema.xml
%{_datadir}/%{sysname}/
%{_metainfodir}/*.appdata.xml


%changelog
* Mon Jan 20 2020 Artem Polishchuk <ego.cordatus@gmail.com> - 0-3.20200120git8121a4f
- Update to latest git snapshot

* Sat Jan 18 2020 Artem Polishchuk <ego.cordatus@gmail.com> - 0-2.20200118git79dc497
- Update to latest git snapshot

* Sat Jan 18 2020 Artem Polishchuk <ego.cordatus@gmail.com> - 0-1.20200118git4cc704a
- Initial package
