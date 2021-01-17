# RecApp

An open-source and user-friendly screencasting app for Linux written in GTK using free GStreamers modules and does not depend on FFmpeg.


<p align="center">
  <img src="https://raw.githubusercontent.com/amikha1lov/RecApp/master/RecApp-screenshot.png" style="max-width:100%;">
</p>


## Packaging status

[Fedora](https://src.fedoraproject.org/rpms/recapp): `sudo dnf install recapp`

[openSUSE Tumbleweed && openSUSE Leap 15.2 One-click installation](https://software.opensuse.org//download.html?project=GNOME%3AApps&package=recapp)

## Build from source

### Flatpak

```
git clone https://github.com/amikha1lov/RecApp.git
cd RecApp
git submodule update --init --recursive
mkdir -p $HOME/Projects/flatpak/repo
flatpak-builder --repo=$HOME/Projects/flatpak/repo --force-clean --ccache build-dir com.github.amikha1lov.RecApp.yaml
flatpak remote-add --no-gpg-verify local-repo $HOME/Projects/flatpak/repo
flatpak install com.github.amikha1lov.RecApp
```
