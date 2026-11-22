#!/usr/bin/env python3
"""Apply the LineGram identity edits to the Telegram-Android tree.

Every edit is an exact text replacement with an expected hit count, so the script
stops instead of guessing if upstream text is not what it expects.
"""
import json
import os
import re
import sys

ROOT = sys.argv[1]
APP_ID = 'org.linegram.messenger'
NAME = 'LineGram'
NAME_AR = 'لاين كرام'
BRAND_FLAT_INT = '0xFFF96B33'

changed = []


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8', newline='') as f:
        return f.read()


def write(rel, text):
    with open(os.path.join(ROOT, rel), 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    changed.append(rel)


def eol_of(text):
    return '\r\n' if '\r\n' in text else '\n'


def patch(rel, edits):
    """edits: list of (old, new, expected_count). new may use \\n; it is adapted to the file's line ends."""
    text = read(rel)
    eol = eol_of(text)
    for old, new, expected in edits:
        old_e = old.replace('\n', eol)
        new_e = new.replace('\n', eol)
        found = text.count(old_e)
        if found != expected:
            raise SystemExit(f'{rel}: expected {expected} x {old!r}, found {found}')
        text = text.replace(old_e, new_e)
    write(rel, text)


def patch_re(rel, edits):
    """edits: list of (regex, replacement, expected_count)."""
    text = read(rel)
    for rx, new, expected in edits:
        text, found = re.subn(rx, lambda m: new, text)
        if found != expected:
            raise SystemExit(f'{rel}: expected {expected} x /{rx}/, found {found}')
    write(rel, text)


GOOGLE_KEY_RX = r'AIza[0-9A-Za-z_-]{35}'   # format of Google API keys

LINEGRAM_ABIS_FN = (
    "// LineGram: CPU types, from LINEGRAM_ABIS in gradle.properties or -PLINEGRAM_ABIS=arm64-v8a\n"
    "def lineGramAbis() {\n"
    "    def value = (project.findProperty(\"LINEGRAM_ABIS\") ?: \"armeabi-v7a,arm64-v8a,x86,x86_64\").toString()\n"
    "    return value.split(\",\").collect { it.trim() }.findAll { !it.isEmpty() }\n"
    "}\n\n")

J = 'TMessagesProj/src/main/java/org/telegram/'
R = 'TMessagesProj/src/main/res/'

# ---- 1. application id + API key slots ------------------------------------------
patch('gradle.properties', [
    ('APP_PACKAGE=org.telegram.messenger\n',
     'APP_PACKAGE=' + APP_ID + '\n'
     '# LineGram: your own Telegram API keys. Create them at https://my.telegram.org\n'
     '# (API development tools). The build stops until both are filled in.\n'
     'TG_API_ID=0\n'
     'TG_API_HASH=\n'
     '# LineGram: CPU types inside the APK. arm64-v8a alone covers phones from about 2017 on.\n'
     'LINEGRAM_ABIS=armeabi-v7a,arm64-v8a,x86,x86_64\n', 1),
])

patch('TMessagesProj/build.gradle', [
    ("    defaultConfig {\n        minSdkVersion 23\n        targetSdkVersion 36\n",
     "    defaultConfig {\n        minSdkVersion 23\n        targetSdkVersion 36\n\n"
     "        // LineGram: Telegram API keys are read from gradle.properties (TG_API_ID / TG_API_HASH)\n"
     "        buildConfigField \"int\", \"TG_API_ID\", lineGramApiId()\n"
     "        buildConfigField \"String\", \"TG_API_HASH\", \"\\\"\" + lineGramApiHash() + \"\\\"\"\n\n"
     "        // LineGram: CPU types of the native libraries, from LINEGRAM_ABIS\n"
     "        ndk {\n"
     "            abiFilters.addAll(lineGramAbis())\n"
     "        }\n", 1),
    ("preBuild.dependsOn checkVisibility\n",
     "preBuild.dependsOn checkVisibility\n\n"
     "// LineGram: API keys from gradle.properties, or from -PTG_API_ID=... -PTG_API_HASH=... on the command line.\n"
     "def lineGramApiId() {\n"
     "    def value = (project.findProperty(\"TG_API_ID\") ?: \"0\").toString().trim()\n"
     "    return value.isInteger() ? value : \"0\"\n"
     "}\n\n"
     "def lineGramApiHash() {\n"
     "    return (project.findProperty(\"TG_API_HASH\") ?: \"\").toString().replaceAll(\"[^0-9a-fA-F]\", \"\")\n"
     "}\n\n"
     + LINEGRAM_ABIS_FN +
     "task checkLineGramApiKeys {\n"
     "    doFirst {\n"
     "        if (lineGramApiId() == \"0\" || lineGramApiHash().isEmpty()) {\n"
     "            throw new GradleException(\"LineGram: fill in TG_API_ID and TG_API_HASH in gradle.properties first. \" +\n"
     "                    \"Create them at https://my.telegram.org (API development tools).\")\n"
     "        }\n"
     "    }\n"
     "}\n\n"
     "preBuild.dependsOn checkLineGramApiKeys\n", 1),
])

patch('TMessagesProj_App/build.gradle', [
    ('        afat {\n            ndk {\n                abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"\n            }\n',
     '        afat {\n            ndk {\n                abiFilters.addAll(lineGramAbis())   // LineGram: from LINEGRAM_ABIS\n            }\n', 1),
    ("apply plugin: 'com.google.gms.google-services'\n",
     "apply plugin: 'com.google.gms.google-services'\n\n" + LINEGRAM_ABIS_FN.rstrip('\n') + "\n", 1),
])

# ---- 2. BuildVars: keys, fork-safe switches --------------------------------------
patch(J + 'messenger/BuildVars.java', [
    ('"https://play.google.com/store/apps/details?id=org.telegram.messenger"',
     '"https://play.google.com/store/apps/details?id=' + APP_ID + '"', 1),
    ('    public static boolean IS_BILLING_UNAVAILABLE = false;\n',
     '    public static boolean IS_BILLING_UNAVAILABLE = true; // LineGram: no Google Play Billing in this fork\n', 1),
    ('    public static boolean SUPPORTS_PASSKEYS = true;\n',
     '    public static boolean SUPPORTS_PASSKEYS = false; // LineGram: passkeys only work with the official app ids\n', 1),
    ('    public static boolean SUPPORTS_FPNV = true;\n',
     '    public static boolean SUPPORTS_FPNV = false; // LineGram: needs the official Firebase project\n', 1),
    ('"org.telegram.messenger.beta".equals(', '"' + APP_ID + '.beta".equals(', 1),
])
patch_re(J + 'messenger/BuildVars.java', [
    (r'    public static int APP_ID = \d+;\n    public static String APP_HASH = "[0-9a-f]{32}";\n',
     '    // LineGram: filled from TG_API_ID / TG_API_HASH in gradle.properties (see LINEGRAM.md)\n'
     '    public static int APP_ID = BuildConfig.TG_API_ID;\n'
     '    public static String APP_HASH = BuildConfig.TG_API_HASH;\n', 1),
    (r'    public static String SAFETYNET_KEY = "' + GOOGLE_KEY_RX + r'";\n',
     '    public static String SAFETYNET_KEY = ""; // LineGram: disabled, the original key belongs to the official app\n', 1),
])

# ---- 3. app name ------------------------------------------------------------------
def rename_strings(rel, name, beta, with_page1, intro=None):
    text = read(rel)
    text, n1 = re.subn(r'(<string name="AppName">)[^<]*(</string>)', lambda m: m.group(1) + name + m.group(2), text)
    text, n2 = re.subn(r'(<string name="AppNameBeta">)[^<]*(</string>)', lambda m: m.group(1) + beta + m.group(2), text)
    text, n3 = re.subn(r'(<string name="Page1Title">)[^<]*(</string>)', lambda m: m.group(1) + name + m.group(2), text)
    n4 = 0
    if intro is not None:
        text, n4 = re.subn(r'(<string name="Page1Message">)[^<]*(</string>)', lambda m: m.group(1) + intro + m.group(2), text)
    if (n1, n2) != (1, 1) or n3 != (1 if with_page1 else 0) or n4 != (0 if intro is None else 1):
        raise SystemExit(f'{rel}: unexpected string counts {n1} {n2} {n3} {n4}')
    write(rel, text)


# Intro text, page 1. Telegram's API terms ask third-party apps to say in the intro that they use the Telegram API.
INTRO = {
    'values': 'An unofficial app that uses the **Telegram API**.\\nIt is **fast**, **free** and **secure**.',
    'values-ar': 'تطبيق غير رسمي يعمل عبر **Telegram API**.\\nإنه **سريع** و**مجاني** و**آمن**.',
    'values-es': 'App no oficial que usa la **API de Telegram**.\\nEs **rápida**, **gratis** y **segura**.',
    'values-pt-rBR': 'Aplicativo não oficial que usa a **API do Telegram**.\\nÉ **rápido**, **gratuito** e **seguro**.',
    'values-ru': 'Неофициальное приложение на **Telegram API**.\\n**Быстрое**, **бесплатное** и **безопасное**.',
    'values-uk': 'Неофіційний застосунок на **Telegram API**.\\n**Швидкий**, **безплатний** і **захищений**.',
}

rename_strings(R + 'values/strings.xml', NAME, NAME + ' Beta', True, INTRO['values'])
rename_strings(R + 'values-ar/strings.xml', NAME_AR, '(Beta) ' + NAME_AR, True, INTRO['values-ar'])
rename_strings(R + 'values-de/strings.xml', NAME, NAME + ' Beta', False)
rename_strings(R + 'values-es/strings.xml', NAME, NAME + ' Beta', True, INTRO['values-es'])
rename_strings(R + 'values-it/strings.xml', NAME, NAME + ' Beta', False)
rename_strings(R + 'values-ko/strings.xml', NAME, NAME + ' Beta', False)
rename_strings(R + 'values-nl/strings.xml', NAME, NAME + '-bèta', False)
rename_strings(R + 'values-pt-rBR/strings.xml', NAME, NAME + ' Beta', True, INTRO['values-pt-rBR'])
rename_strings(R + 'values-ru/strings.xml', NAME, NAME + ' Beta', True, INTRO['values-ru'])
rename_strings(R + 'values-uk/strings.xml', NAME, NAME + ' Beta', True, INTRO['values-uk'])

# keep the app's own name out of reach of downloaded Telegram language packs
patch(J + 'messenger/LocaleController.java', [
    ('        if (BuildVars.USE_CLOUD_STRINGS) {\n            value = localizationExternal.getByResNameOrResId(context, key, stringRes);\n',
     '        // LineGram: the app\'s own name and intro notice always come from the bundled strings,\n'
     '        // so a downloaded Telegram language pack cannot change them back.\n'
     '        if (BuildVars.USE_CLOUD_STRINGS && !isBrandString(key, stringRes)) {\n'
     '            value = localizationExternal.getByResNameOrResId(context, key, stringRes);\n', 1),
    ('    @Nullable\n    private String getStringV2(String key, @StringRes int stringRes, String fallback) {\n',
     '    private static boolean isBrandString(String key, @StringRes int stringRes) {\n'
     '        if (stringRes != 0 && (stringRes == R.string.AppName || stringRes == R.string.AppNameBeta || stringRes == R.string.Page1Title || stringRes == R.string.Page1Message)) {\n'
     '            return true;\n'
     '        }\n'
     '        return "AppName".equals(key) || "AppNameBeta".equals(key) || "Page1Title".equals(key) || "Page1Message".equals(key);\n'
     '    }\n\n'
     '    @Nullable\n    private String getStringV2(String key, @StringRes int stringRes, String fallback) {\n', 1),
])

# ---- 4. intro logo colour ---------------------------------------------------------
patch(J + 'ui/IntroActivity.java', [
    ("                paint.setColor(ThemeColors.TELEGRAM_COLOR); // It's logo color, it should not be colored by the theme\n",
     "                paint.setColor(" + BRAND_FLAT_INT + "); // LineGram logo colour, it should not be colored by the theme\n", 1),
])

# ---- 5. system account type, contact data types, account-settings shortcut ----------
patch(J + 'messenger/ContactsController.java', [
    ('"org.telegram.messenger"', '"' + APP_ID + '"', 5),
    ('vnd.org.telegram.messenger.android.', 'vnd.' + APP_ID + '.android.', 3),
])
patch(J + 'ui/LaunchActivity.java', [
    ('vnd.org.telegram.messenger.android.', 'vnd.' + APP_ID + '.android.', 2),
])
patch('TMessagesProj/src/main/AndroidManifest.xml', [
    ('vnd.org.telegram.messenger.android.', 'vnd.' + APP_ID + '.android.', 3),
])
patch(R + 'xml/contacts.xml', [
    ('vnd.org.telegram.messenger.android.', 'vnd.' + APP_ID + '.android.', 3),
])
patch(R + 'xml/auth.xml', [('android:accountType="org.telegram.messenger"', 'android:accountType="' + APP_ID + '"', 1)])
patch(R + 'xml/sync_contacts.xml', [('android:accountType="org.telegram.messenger"', 'android:accountType="' + APP_ID + '"', 1)])
patch(R + 'xml/auth_menu.xml', [('android:targetPackage="org.telegram.messenger"', 'android:targetPackage="' + APP_ID + '"', 1)])

# ---- 6. Google keys that belong to the official app ------------------------------
MAPS_RX = r'(android:name="com\.google\.android\.maps\.v2\.API_KEY" android:value=")' + GOOGLE_KEY_RX + '"'
MAPS_NEW = 'android:name="com.google.android.maps.v2.API_KEY" android:value="YOUR_GOOGLE_MAPS_API_KEY"'
for rel in ('TMessagesProj/config/debug/AndroidManifest.xml', 'TMessagesProj/config/debug/AndroidManifest_SDK23.xml',
            'TMessagesProj/config/release/AndroidManifest.xml', 'TMessagesProj/config/release/AndroidManifest_SDK23.xml',
            'TMessagesProj/config/release/AndroidManifest_standalone.xml'):
    patch_re(rel, [(MAPS_RX, MAPS_NEW, 1)])

# Placeholder Firebase file: right package names so the build passes, no real project behind it.
# Firebase only checks the shape "A + 38 letters/digits/_/-". This value has that shape, but it is not
# shaped like a real Google key (those start with "AIza"), so nobody mistakes it for one.
PLACEHOLDER_KEY = 'ALINEGRAM_PLACEHOLDER_KEY_REPLACE_ME_00'
assert re.fullmatch(r'A[\w-]{38}', PLACEHOLDER_KEY) and not re.match(GOOGLE_KEY_RX, PLACEHOLDER_KEY), PLACEHOLDER_KEY
PLACEHOLDER_OAUTH = '000000000000-linegramplaceholder.apps.googleusercontent.com'


def client(package, suffix):
    return {
        'client_info': {
            'mobilesdk_app_id': '1:000000000000:android:' + suffix,
            'android_client_info': {'package_name': package},
        },
        'oauth_client': [{'client_id': PLACEHOLDER_OAUTH, 'client_type': 3}],
        'api_key': [{'current_key': PLACEHOLDER_KEY}],
        'services': {'appinvite_service': {'other_platform_oauth_client': [{'client_id': PLACEHOLDER_OAUTH, 'client_type': 3}]}},
    }


google_services = {
    'project_info': {
        'project_number': '000000000000',
        'firebase_url': 'https://linegram-placeholder.firebaseio.com',
        'project_id': 'linegram-placeholder',
        'storage_bucket': 'linegram-placeholder.appspot.com',
    },
    'client': [
        client(APP_ID, '0000000000000001'),
        client(APP_ID + '.beta', '0000000000000002'),
        client(APP_ID + '.web', '0000000000000003'),
        # internal package (namespace) of the TMessagesProj library module, used by the build plugin only
        client('org.telegram.messenger', '0000000000000004'),
    ],
    'configuration_version': '1',
}
for rel in ('TMessagesProj/google-services.json', 'TMessagesProj_App/google-services.json',
            'TMessagesProj_AppStandalone/google-services.json', 'TMessagesProj_AppHockeyApp/google-services.json',
            'TMessagesProj_AppHuawei/google-services.json'):
    write(rel, json.dumps(google_services, indent=2) + '\n')

# Huawei module: same package id in its service file, so the ids agree if that module is ever configured
patch('TMessagesProj_AppHuawei/agconnect-services.json', [('"package_name":"org.telegram.messenger"', '"package_name":"' + APP_ID + '"', 4)])

print(len(changed), 'files changed')
for c in changed:
    print('  ', c)
