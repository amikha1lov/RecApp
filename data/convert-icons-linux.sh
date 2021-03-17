#!/bin/bash

base=com.github.amikha1lov.RecApp.svg
endname=com.github.amikha1lov.RecApp
convert "$base" -resize '24x24'     -unsharp 1x4 "$endname-24.png"
convert "$base" -resize '32x32'     -unsharp 1x4 "$endname-32.png"
convert "$base" -resize '48x48'     -unsharp 1x4 "$endname-48.png"
convert "$base" -resize '64x64'     -unsharp 1x4 "$endname-64.png"
convert "$base" -resize '96x96'     -unsharp 1x4 "$endname-96.png"
convert "$base" -resize '128x128'   -unsharp 1x4 "$endname-128.png"
convert "$base" -resize '192x192'   -unsharp 1x4 "$endname-192.png"
convert "$base" -resize '256x256'   -unsharp 1x4 "$endname-256.png"