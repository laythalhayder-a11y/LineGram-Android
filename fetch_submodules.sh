#!/usr/bin/env bash
# LineGram: download the 22 source folders that a GitHub "Download ZIP" leaves empty
# (git submodules), each at the exact commit pinned by upstream Telegram 13.2.2 (7303),
# commit 21f7d109da6ab3506c9e9577f98c6a38771ab335.
#
# Usage (Linux / macOS / Git Bash on Windows), from the project root:
#     ./fetch_submodules.sh
# Safe to re-run: folders that are already filled are skipped.
# Needs: git + internet access. Downloads about 1.1 GB.

set -u
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

# path | url | pinned commit | optional mirror url (same commit id = identical content)
MODULES="
TMessagesProj/jni/tlottie|https://github.com/dkaraush/tlottie.git|31f1b542f88e7b4be9a01e749920d857535fc715|
TMessagesProj/jni/third_party/libvpx|https://github.com/webmproject/libvpx.git|6df3ec34557879fff673706f4a1d9fbd0f3a6f0e|
TMessagesProj/jni/third_party/dav1d|https://github.com/videolan/dav1d.git|54706fc6bc0cdecab7e9593974a4039cc038fca7|
TMessagesProj/jni/third_party/ffmpeg|https://github.com/FFmpeg/FFmpeg.git|8dca1586f468bfcbb78ae3ed618af1361d9f140a|
TMessagesProj/lib/jlatexmath|https://github.com/dkaraush/jlatexmath-android.git|919e50b2f6f64b04b712cdb13d558ff9ecf9c8ed|
TMessagesProj/jni/third_party/xiph/ogg|https://github.com/xiph/ogg.git|be05b13e98b048f0b5a0f5fa8ce514d56db5f822|
TMessagesProj/jni/third_party/xiph/opusfile|https://github.com/xiph/opusfile.git|a55c164e9891a9326188b7d4d216ec9a88373739|
TMessagesProj/jni/third_party/xiph/opus|https://github.com/xiph/opus.git|22244de5a79bd1d6d623c32e72bf1954b56235be|
TMessagesProj/jni/third_party/libyuv|https://chromium.googlesource.com/libyuv/libyuv|28ce69c2744a6aafdb58564e7b884aec3f66be5f|https://github.com/lemenkov/libyuv.git
TMessagesProj/jni/third_party/openh264|https://github.com/cisco/openh264.git|652bdb7719f30b52b08e506645a7322ff1b2cc6f|
TMessagesProj/jni/third_party/boringssl|https://github.com/google/boringssl.git|2b44a3701a4788e1ef866ddc7f143060a3d196c9|
TMessagesProj/jni/td|https://github.com/tdlib/td.git|022d60202e446ad1287b9fb68e687c8a0760788b|
TMessagesProj_Modules/media|https://github.com/Arseny271/media.git|09b6c97c0d691c50cd4541e1573995d4066d6f5c|
TMessagesProj/jni/third_party/absl|https://github.com/abseil/abseil-cpp.git|54fac219c4ef0bc379dfffb0b8098725d77ac81b|
TMessagesProj/jni/third_party/wamr|https://github.com/wasm-micro-runtime/wasm-micro-runtime.git|25bd7eb63e828e4bd242cc9b38d260b4b31c6605|
TMessagesProj/jni/tgcalls|https://github.com/TelegramMessenger/tgcalls.git|545f5ae599f8282e1ae3f38aaff166d179d75703|
TMessagesProj/jni/wallet-engine|https://github.com/dkaraush/wallet-engine.git|5c65e47cb8d68727c20d89382d0bc51292486b9a|
TMessagesProj/jni/third_party/boost-regex|https://github.com/boostorg/regex.git|4cbcd3078e6ae10d05124379623a1bf03fcb9350|
TMessagesProj/jni/third_party/libprisma|https://github.com/TelegramMessenger/libprisma.git|94640c63c20eacdf70e37e23198d9ab53c802ebd|
TMessagesProj/jni/twidget/twidget|https://github.com/TelegramMessenger/twidget.git|4769d72c5c5a9bace3c7bd8b6308cb79bc150bab|
TMessagesProj/jni/twidget/widget-sandbox|https://github.com/TelegramMessenger/widget-sandbox.git|c498cefddefaba765282c9f3ab0b330f4bc990f6|
TMessagesProj/jni/twidget/widget-sandbox/packages/ios/Sources/CQuickJS/quickjs|https://github.com/TelegramMessenger/quickjs.git|ca3594dae5fd0dd6d667be74a322e8e935a2d217|
"

fetch_commit() {  # <dir> <url> <sha>  -> 0 when <dir> holds exactly <sha>
    local dir="$1" url="$2" sha="$3" got
    rm -rf "$dir/.git"
    git -C "$dir" init -q || return 1
    git -C "$dir" remote add origin "$url" || return 1
    git -C "$dir" -c protocol.version=2 fetch -q --depth 1 origin "$sha" || return 1
    git -C "$dir" -c advice.detachedHead=false checkout -q -f FETCH_HEAD || return 1
    got="$(git -C "$dir" rev-parse HEAD)"
    [ "$got" = "$sha" ]
}

ok=0; skipped=0; failed=0
while IFS='|' read -r path url sha mirror; do
    [ -n "${path:-}" ] || continue
    if [ -d "$path" ] && [ -n "$(ls -A "$path" 2>/dev/null)" ]; then
        echo "skip  $path (already filled)"
        skipped=$((skipped + 1))
        continue
    fi
    mkdir -p "$path"
    echo "fetch $path"
    if fetch_commit "$path" "$url" "$sha"; then
        :
    elif [ -n "$mirror" ] && echo "      main address failed, trying mirror $mirror" && fetch_commit "$path" "$mirror" "$sha"; then
        :
    else
        echo "FAILED $path  ($url @ $sha)" >&2
        rm -rf "$path/.git"
        failed=$((failed + 1))
        continue
    fi
    # Plain folder from here on: the commit id above already proved the content.
    rm -rf "$path/.git"
    ok=$((ok + 1))
done <<EOF
$MODULES
EOF

echo
echo "downloaded: $ok   already there: $skipped   failed: $failed"
if [ "$failed" -ne 0 ]; then
    echo "Some folders failed. Check the internet connection and run this script again." >&2
    exit 1
fi
echo "All source folders are complete."
