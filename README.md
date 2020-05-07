# RecApp


User friendly Open Source screencaster for Linux written in GTK. Using free GStreamer modules and not depend on FFmpeg.


<p align="center">
  <img src="https://raw.githubusercontent.com/amikha1lov/RecApp/master/RecApp-screenshot.png" style="max-width:100%;">
</p>


## Packaging status

Fedora [COPR](https://copr.fedorainfracloud.org/coprs/atim/rec-app/):

```
sudo dnf copr enable atim/rec-app -y
sudo dnf install recapp
```

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
