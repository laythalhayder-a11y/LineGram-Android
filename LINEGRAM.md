# LineGram for Android

LineGram is built from the official Telegram for Android source, version 13.2.2 (7303),
upstream commit `21f7d109da6ab3506c9e9577f98c6a38771ab335`. Only the identity was changed.
All Telegram features and screens are untouched.

LineGram is an unofficial Telegram client. It talks to Telegram's servers. People log in
with their Telegram phone number and see their Telegram chats. It is not a separate network.

## Status

| Part | State |
|------|-------|
| Source code | Complete. All 14,160 original files match Telegram's GitHub repository. The 22 third-party folders missing from the ZIP download are fetched by `fetch_submodules.sh`. |
| Rename to LineGram | Done and checked: Java syntax of the edited files, every edited XML and JSON file, pixel size and format of every replaced image. |
| APK | Builds on GitHub: the first run finished the whole Gradle build in 16 minutes (arm64). Not tested on a phone yet. |

## 1. Three things to do before the first build

| # | What | Where |
|---|------|-------|
| 1 | Get your own Telegram API keys | https://my.telegram.org → API development tools. App title: LineGram. Platform: Android. |
| 2 | Give the build your keys | GitHub build: repository secrets `TG_API_ID` and `TG_API_HASH` (section 2). Build on your own computer: the same two lines in `gradle.properties`. |
| 3 | Download the third-party source folders | run `./fetch_submodules.sh` (about 1.1 GB, needs git) |

On your own computer the build stops with a clear message while the keys are missing.
Step 3 is automatic in the GitHub build below.

## 2. Build the APK on GitHub (no computer setup)

1. Create a new **public** repository on GitHub and upload this project to it with GitHub Desktop or git.
   The web page cannot take 14,000 files at once.
2. Add your keys as secrets: Settings → Secrets and variables → Actions → New repository secret,
   once for `TG_API_ID` and once for `TG_API_HASH`. Never write them into `gradle.properties` in a public
   repository: everyone can read that file.
3. The build starts by itself after every push to `main`. To start it by hand:
   **Actions → Build LineGram APK → Run workflow**. One build takes about half an hour.
4. When the run is green, open **Releases** on the repository page and download the `.apk` file.
   This works from the phone too. The same APK is also under Artifacts at the bottom of the run page.

Without the two secrets the build still runs, but it makes a test APK that cannot log in, and no release.
The log of the last build is saved on the `build-logs` branch (`summary.txt`, `errors.txt`, `build.log`).

A public repository gets the larger free build machine (4 cores, 16 GB). A private one gets 2 cores and 8 GB, which is probably too small for this build.

## 3. Build the APK on your own computer

You need Android Studio, Android SDK 36, Build-Tools 36.0.0, NDK 27.2.12479018, CMake 3.22.1,
git, about 16 GB of RAM and about 40 GB of free disk space.

1. Fill in the keys in `gradle.properties`.
2. Run `./fetch_submodules.sh` (on Windows: right-click the folder → Git Bash Here).
3. Open the folder in Android Studio (Open, not Import) and wait for the sync.
4. Run: `./gradlew :TMessagesProj_App:assembleAfatRelease`
5. The APK is in `TMessagesProj_App/build/outputs/apk/afat/release/app.apk`.

On Windows keep the project in a short path such as `C:\lg`. Long paths can break the native build.

## 4. What was changed

| Area | Change |
|------|--------|
| App id | `org.telegram.messenger` → `org.linegram.messenger` (`APP_PACKAGE` in `gradle.properties`) |
| App name | `LineGram` / `لاين كرام` in all bundled languages. Downloaded language packs cannot rename it. |
| Logo | New launcher icons (all six variants), notification icon, splash, intro logo, header wordmark, QR-code logo and its animation |
| API keys | Read from `gradle.properties` instead of the public sample keys |
| Account and contact ids | Own Android account type and contact data types, so LineGram and Telegram can be installed side by side |
| Official-only features | Passkeys, Google Play Billing, SafetyNet and Firebase phone verification are switched off |
| Official Google keys | The Maps key, the SafetyNet key and the Firebase file of the official app were replaced by placeholders. See section 5. |

`linegram_branding/make_brand.py` redraws every logo file. Change the colours at the top of that file and run it again.
`linegram_branding/apply_rebrand.py` lists every text edit made to the Telegram source. Run it as
`python3 linegram_branding/apply_rebrand.py <folder>` to make the same edits on a fresh copy of this Telegram version.

## 5. Things that need your own accounts

| Feature | State now | What it needs |
|---------|-----------|---------------|
| Push notifications when the app is closed | Off | Your own Firebase project for `org.linegram.messenger`. Replace `TMessagesProj_App/google-services.json`, then upload the Firebase key at my.telegram.org. Leave `TMessagesProj/google-services.json` as it is. |
| Maps in location sharing | Blank map | Your own Google Maps key. Replace `YOUR_GOOGLE_MAPS_API_KEY` in `TMessagesProj/config/*/AndroidManifest*.xml`. |
| Signing key | Public test key from Telegram's source | Your own keystore before you give the APK to other people. |
| Login code by SMS auto-fill | Off | Type the code by hand. The code usually arrives inside your official Telegram app. |

Messages still arrive while LineGram is open or still running in the background.

## 6. Telegram's rules for apps made from its source

From the README of the source and the Telegram API Terms of Service (https://core.telegram.org/api/terms):

1. Use your own `api_id`. One phone number can hold one `api_id`.
2. Do not put "Telegram" in the app title, and do not use Telegram's logo.
3. Say in the store description and in the app intro that the app uses the Telegram API. The intro of LineGram already says so.
4. Do not break basic Telegram behaviour: read status, online status, typing status, self-destructing media, sponsored messages in channels.
5. Protect your users' data and privacy.
6. Publish your source code. The licence is GNU GPL v2 or later (see `LICENSE`).
7. List every way the app makes money in the store description.

Telegram watches accounts that log in from unofficial apps more closely. Breaking the terms can end API access for the app.

Texts inside the app still say "Telegram" where they mean the Telegram service, for example
"Telegram Premium". That is correct for a Telegram client.

The modules `TMessagesProj_AppStandalone`, `TMessagesProj_AppHuawei` and `TMessagesProj_AppHockeyApp`
were not prepared for LineGram. Build `TMessagesProj_App` only.
