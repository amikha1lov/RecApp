%global commit      4cc704a99847279004137ec7cac8a7fca383bdc7
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global date        20200118

%global uuid    com.github.amikha1lov.rec_app

Name:           rec_app
Version:        0
Release:        1.%{date}git%{shortcommit}%{?dist}
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
#Recommends:     gstreamer1-plugins-ugly

%description
%{summary}.


%prep
%autosetup -n rec_app-%{commit} -p1


%build
%meson
%meson_build


%install
%meson_install
#%%find_lang %{uuid}


%check
#appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/*.xml
desktop-file-validate %{buildroot}%{_datadir}/applications/*.desktop


%files
%license COPYING
#%%doc README.md
%{_bindir}/rec_app
%{_datadir}/appdata/*.appdata.xml
%{_datadir}/applications/*.desktop
%{_datadir}/glib-2.0/schemas/*.gschema.xml
%{_datadir}/rec_app/


%changelog
* Sat Jan 18 2020 Artem Polishchuk <ego.cordatus@gmail.com> - 0-1.20200118git4cc704a
- Initial package
