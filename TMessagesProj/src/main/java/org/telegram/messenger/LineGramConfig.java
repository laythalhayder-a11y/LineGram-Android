package org.telegram.messenger;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Typeface;

import org.telegram.messenger.time.FastDateFormat;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.Theme;

import java.util.Locale;

/**
 * LineGram: the app's own switches, kept in their own preferences file so they
 * never mix with Telegram's settings. Every feature the user asked for is on by
 * default; each one can be turned off from Settings > LineGram Settings.
 */
public class LineGramConfig {

    /** The folder name used for saved photos, videos, music and downloads. */
    public static final String FOLDER = "LineGram";

    public static final String KEY_CONFIRM_VOICE = "confirm_voice";
    public static final String KEY_CONFIRM_STICKER = "confirm_sticker";
    public static final String KEY_CONFIRM_GIF = "confirm_gif";
    public static final String KEY_HIDE_STORIES = "hide_stories";
    public static final String KEY_HIDE_PREMIUM = "hide_premium";
    public static final String KEY_SHOW_ID = "show_id";
    public static final String KEY_TIME_SECONDS = "time_seconds";
    public static final String KEY_FULL_DATE = "full_date";
    public static final String KEY_HIDE_PHONE = "hide_phone";
    public static final String KEY_FONT = "chat_font";

    public static final int FONT_SYSTEM = 0;
    public static final int FONT_CAIRO = 1;
    public static final int FONT_TAJAWAL = 2;

    /** The orange accent: its id is 4 in the Blue, Dark Blue, Arctic Blue and Night themes. */
    public static final int ORANGE_ACCENT_ID = 4;

    private static final String PREFS_NAME = "linegram_config";

    private static final Object lock = new Object();
    private static volatile boolean loaded;

    private static volatile boolean confirmVoice;
    private static volatile boolean confirmSticker;
    private static volatile boolean confirmGif;
    private static volatile boolean hideStories;
    private static volatile boolean hidePremium;
    private static volatile boolean showId;
    private static volatile boolean timeSeconds;
    private static volatile boolean fullDate;
    private static volatile boolean hidePhone;
    private static volatile int chatFont;

    private static volatile FastDateFormat fullDateFormat;
    private static volatile String fullDateFormatKey;

    private static SharedPreferences prefs() {
        return ApplicationLoader.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    private static void ensureLoaded() {
        if (loaded) {
            return;
        }
        synchronized (lock) {
            if (loaded) {
                return;
            }
            if (ApplicationLoader.applicationContext == null) {
                return;
            }
            final SharedPreferences p = prefs();
            confirmVoice = p.getBoolean(KEY_CONFIRM_VOICE, true);
            confirmSticker = p.getBoolean(KEY_CONFIRM_STICKER, true);
            confirmGif = p.getBoolean(KEY_CONFIRM_GIF, true);
            hideStories = p.getBoolean(KEY_HIDE_STORIES, true);
            hidePremium = p.getBoolean(KEY_HIDE_PREMIUM, true);
            showId = p.getBoolean(KEY_SHOW_ID, true);
            timeSeconds = p.getBoolean(KEY_TIME_SECONDS, true);
            fullDate = p.getBoolean(KEY_FULL_DATE, true);
            hidePhone = p.getBoolean(KEY_HIDE_PHONE, true);
            chatFont = p.getInt(KEY_FONT, FONT_CAIRO);
            loaded = true;
        }
    }

    public static boolean get(String key) {
        ensureLoaded();
        switch (key) {
            case KEY_CONFIRM_VOICE: return confirmVoice;
            case KEY_CONFIRM_STICKER: return confirmSticker;
            case KEY_CONFIRM_GIF: return confirmGif;
            case KEY_HIDE_STORIES: return hideStories;
            case KEY_HIDE_PREMIUM: return hidePremium;
            case KEY_SHOW_ID: return showId;
            case KEY_TIME_SECONDS: return timeSeconds;
            case KEY_FULL_DATE: return fullDate;
            case KEY_HIDE_PHONE: return hidePhone;
        }
        return false;
    }

    public static void set(String key, boolean value) {
        ensureLoaded();
        switch (key) {
            case KEY_CONFIRM_VOICE: confirmVoice = value; break;
            case KEY_CONFIRM_STICKER: confirmSticker = value; break;
            case KEY_CONFIRM_GIF: confirmGif = value; break;
            case KEY_HIDE_STORIES: hideStories = value; break;
            case KEY_HIDE_PREMIUM: hidePremium = value; break;
            case KEY_SHOW_ID: showId = value; break;
            case KEY_TIME_SECONDS: timeSeconds = value; break;
            case KEY_FULL_DATE: fullDate = value; break;
            case KEY_HIDE_PHONE: hidePhone = value; break;
            default: return;
        }
        prefs().edit().putBoolean(key, value).apply();
    }

    public static boolean toggle(String key) {
        final boolean value = !get(key);
        set(key, value);
        return value;
    }

    public static boolean confirmVoice() {
        return get(KEY_CONFIRM_VOICE);
    }

    public static boolean confirmSticker() {
        return get(KEY_CONFIRM_STICKER);
    }

    public static boolean confirmGif() {
        return get(KEY_CONFIRM_GIF);
    }

    public static boolean hideStories() {
        return get(KEY_HIDE_STORIES);
    }

    public static boolean hidePremium() {
        return get(KEY_HIDE_PREMIUM);
    }

    public static boolean showId() {
        return get(KEY_SHOW_ID);
    }

    public static boolean timeSeconds() {
        return get(KEY_TIME_SECONDS);
    }

    public static boolean fullDate() {
        return get(KEY_FULL_DATE);
    }

    public static boolean hidePhone() {
        return get(KEY_HIDE_PHONE);
    }

    public static int chatFont() {
        ensureLoaded();
        return chatFont;
    }

    public static void setChatFont(int font) {
        ensureLoaded();
        chatFont = font;
        prefs().edit().putInt(KEY_FONT, font).apply();
    }

    /** The clearer Arabic font for message text, or null for the phone's own font. */
    public static Typeface messageTypeface() {
        switch (chatFont()) {
            case FONT_CAIRO:
                return AndroidUtilities.getTypeface("fonts/lg_cairo.ttf");
            case FONT_TAJAWAL:
                return AndroidUtilities.getTypeface("fonts/lg_tajawal.ttf");
            default:
                return null;
        }
    }

    /** LineGram's orange is the default accent of the built-in themes that have it. */
    public static int defaultAccentId(String themeName, int telegramDefault) {
        if ("Blue".equals(themeName) || "Dark Blue".equals(themeName) || "Arctic Blue".equals(themeName) || "Night".equals(themeName)) {
            return ORANGE_ACCENT_ID;
        }
        return telegramDefault;
    }

    /** The time shown inside a message bubble: with seconds when the user asked for them. */
    public static FastDateFormat messageTimeFormatter() {
        final LocaleController localeController = LocaleController.getInstance();
        return timeSeconds() ? localeController.getFormatterDayWithSeconds() : localeController.getFormatterDay();
    }

    /** A message's full date and time, with the weekday and the seconds. */
    public static String formatFullDate(int unixTime) {
        Locale locale = LocaleController.getInstance().getCurrentLocale();
        if (locale == null) {
            locale = Locale.getDefault();
        }
        final String pattern = "EEEE, d MMMM yyyy, " + (LocaleController.is24HourFormat ? "HH:mm:ss" : "h:mm:ss a");
        final String key = locale + "|" + pattern;
        FastDateFormat formatter = fullDateFormat;
        if (formatter == null || !key.equals(fullDateFormatKey)) {
            try {
                formatter = FastDateFormat.getInstance(pattern, locale);
            } catch (Exception e) {
                FileLog.e(e);
                formatter = FastDateFormat.getInstance(pattern, Locale.US);
            }
            fullDateFormat = formatter;
            fullDateFormatKey = key;
        }
        return formatter.format((long) unixTime * 1000L);
    }

    /** A chat's ID the way bots and other apps write it: -100… for channels and supergroups. */
    public static String chatIdText(long chatId, boolean isChannel) {
        return isChannel ? "-100" + chatId : "-" + chatId;
    }

    /** Asks before sending, so a sticker, GIF or voice message is not sent by mistake. */
    public static void confirmSend(Context context, Theme.ResourcesProvider resourcesProvider, CharSequence message, Runnable onSend, Runnable onCancel) {
        if (context == null) {
            if (onSend != null) {
                onSend.run();
            }
            return;
        }
        try {
            final boolean[] sent = new boolean[1];
            final AlertDialog.Builder builder = new AlertDialog.Builder(context, resourcesProvider);
            builder.setTitle(LocaleController.getString(R.string.LineGramConfirmTitle));
            builder.setMessage(message);
            builder.setPositiveButton(LocaleController.getString(R.string.Send), (di, which) -> {
                sent[0] = true;
                if (onSend != null) {
                    onSend.run();
                }
            });
            builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
            final AlertDialog dialog = builder.create();
            dialog.setOnDismissListener(d -> {
                if (!sent[0] && onCancel != null) {
                    onCancel.run();
                }
            });
            dialog.show();
        } catch (Exception e) {
            FileLog.e(e);
            if (onSend != null) {
                onSend.run();
            }
        }
    }
}
