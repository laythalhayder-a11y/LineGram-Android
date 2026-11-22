package org.telegram.messenger;

import android.text.TextUtils;

import com.google.mlkit.common.model.DownloadConditions;
import com.google.mlkit.nl.translate.TranslateLanguage;
import com.google.mlkit.nl.translate.Translation;
import com.google.mlkit.nl.translate.Translator;
import com.google.mlkit.nl.translate.TranslatorOptions;

/**
 * LineGram: translates text to Arabic on the phone itself (Google ML Kit).
 * The first time a language is used its files (about 30 MB) are downloaded;
 * after that the translation works with no internet.
 */
public class LineGramTranslator {

    public interface Callback {
        /** Either the translation, or a string resource that explains why there is none. */
        void run(String translation, int errorRes);
    }

    public static void translateToArabic(String text, Callback callback) {
        if (TextUtils.isEmpty(text) || TextUtils.isEmpty(text.trim())) {
            finish(callback, null, R.string.LineGramTranslateFailed);
            return;
        }
        LanguageDetector.detectLanguage(text, language -> {
            if (language == null || "und".equals(language)) {
                // ML Kit could not tell the language; most such texts in chats are English
                translate(text, TranslateLanguage.ENGLISH, callback);
            } else if (language.startsWith("ar")) {
                finish(callback, null, R.string.LineGramTranslateAlreadyArabic);
            } else {
                final String source = TranslateLanguage.fromLanguageTag(language);
                if (source == null) {
                    finish(callback, null, R.string.LineGramTranslateUnsupported);
                } else {
                    translate(text, source, callback);
                }
            }
        }, e -> translate(text, TranslateLanguage.ENGLISH, callback));
    }

    private static void translate(String text, String source, Callback callback) {
        final Translator translator;
        try {
            final TranslatorOptions options = new TranslatorOptions.Builder()
                    .setSourceLanguage(source)
                    .setTargetLanguage(TranslateLanguage.ARABIC)
                    .build();
            translator = Translation.getClient(options);
        } catch (Throwable e) {
            FileLog.e(e);
            finish(callback, null, R.string.LineGramTranslateFailed);
            return;
        }
        translator.downloadModelIfNeeded(new DownloadConditions.Builder().build())
                .addOnSuccessListener(unused -> translator.translate(text)
                        .addOnSuccessListener(result -> {
                            finish(callback, result, 0);
                            translator.close();
                        })
                        .addOnFailureListener(e -> {
                            FileLog.e(e);
                            finish(callback, null, R.string.LineGramTranslateFailed);
                            translator.close();
                        }))
                .addOnFailureListener(e -> {
                    FileLog.e(e);
                    finish(callback, null, R.string.LineGramTranslateFailed);
                    translator.close();
                });
    }

    private static void finish(Callback callback, String translation, int errorRes) {
        if (callback == null) {
            return;
        }
        AndroidUtilities.runOnUIThread(() -> callback.run(translation, errorRes));
    }
}
