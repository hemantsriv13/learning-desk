# Learning Desk for Android

The phone version of Learning Desk, built with Expo (React Native). Same lessons, colours, fonts and pixel art
as the desktop app. Progress, quick-check answers and notes are saved **on the phone only**.

## Try it on your phone (no build needed)

1. Install **Expo Go** from the Play Store.
2. On this computer, in this folder: `npm install` (first time only), then `npx expo start`.
3. Scan the QR code with Expo Go. Phone and computer must be on the same Wi-Fi.

## Build an installable APK

Builds run in Expo's cloud (free tier is enough); no Android Studio needed.

```
npx eas-cli@latest login
npx eas-cli@latest build -p android --profile preview
```

When it finishes, open the link on your phone to download and install the APK.

## Updating lessons

Lessons live in the desktop app (`learning_desk/curriculum`). After changing them, from the repository root:

```
.venv\Scripts\python tools\export_mobile.py
```

This rewrites `assets/content.json`, which is the only content the app reads.

## Checks

`npx tsc --noEmit` (types) and `npx expo export --platform android` (bundles the app).
