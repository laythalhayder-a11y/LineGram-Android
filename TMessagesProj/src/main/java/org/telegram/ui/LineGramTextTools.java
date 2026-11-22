package org.telegram.ui;

import static org.telegram.messenger.LocaleController.getString;

import android.app.Activity;
import android.os.Build;
import android.text.TextUtils;
import android.widget.Toast;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LineGramOcr;
import org.telegram.messenger.LineGramTranslator;
import org.telegram.messenger.R;
import org.telegram.messenger.Utilities;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.Theme;

/**
 * LineGram: the windows for "copy text from image" and "translate to Arabic offline".
 * The caller passes how to show a dialog, so this works over the photo viewer and in chats.
 */
public class LineGramTextTools {

    /** Reads the text in a photo and shows it with Copy and Translate buttons. */
    public static void showTextFromImage(Activity activity, Theme.ResourcesProvider resourcesProvider, String imagePath, Utilities.Callback<AlertDialog.Builder> presenter) {
        if (activity == null || TextUtils.isEmpty(imagePath)) {
            return;
        }
        final AlertDialog progress = showProgress(activity, resourcesProvider, getString(R.string.LineGramOcrWorking));
        LineGramOcr.recognize(imagePath, text -> {
            dismiss(progress);
            if (text == null) {
                presenter.run(message(activity, resourcesProvider, getString(R.string.LineGramOcrTitle), getString(R.string.LineGramOcrFailed)));
            } else if (text.isEmpty()) {
                presenter.run(message(activity, resourcesProvider, getString(R.string.LineGramOcrTitle), getString(R.string.LineGramOcrNothing)));
            } else {
                presenter.run(textResult(activity, resourcesProvider, getString(R.string.LineGramOcrTitle), text, true, presenter));
            }
        });
    }

    /** Translates text to Arabic on the phone and shows the result. */
    public static void translateToArabic(Activity activity, Theme.ResourcesProvider resourcesProvider, String text, Utilities.Callback<AlertDialog.Builder> presenter) {
        if (activity == null || TextUtils.isEmpty(text)) {
            return;
        }
        final AlertDialog progress = showWaitMessage(activity, resourcesProvider, getString(R.string.LineGramTranslateTitle), getString(R.string.LineGramTranslateWorking));
        LineGramTranslator.translateToArabic(text, (translation, errorRes) -> {
            dismiss(progress);
            if (translation != null) {
                presenter.run(textResult(activity, resourcesProvider, getString(R.string.LineGramTranslateTitle), translation, false, presenter));
            } else {
                presenter.run(message(activity, resourcesProvider, getString(R.string.LineGramTranslateTitle), getString(errorRes != 0 ? errorRes : R.string.LineGramTranslateFailed)));
            }
        });
    }

    private static AlertDialog.Builder textResult(Activity activity, Theme.ResourcesProvider resourcesProvider, String title, String text, boolean offerTranslate, Utilities.Callback<AlertDialog.Builder> presenter) {
        final AlertDialog.Builder builder = new AlertDialog.Builder(activity, resourcesProvider);
        builder.setTitle(title);
        builder.setMessage(text);
        builder.setPositiveButton(getString(R.string.Copy), (dialog, which) -> {
            if (AndroidUtilities.addToClipboard(text) && Build.VERSION.SDK_INT < 33) {
                // Android 13 and newer show their own "copied" message
                Toast.makeText(activity, getString(R.string.TextCopied), Toast.LENGTH_SHORT).show();
            }
        });
        if (offerTranslate) {
            builder.setNeutralButton(getString(R.string.LineGramTranslateShort), (dialog, which) -> translateToArabic(activity, resourcesProvider, text, presenter));
        }
        builder.setNegativeButton(getString(R.string.Close), null);
        return builder;
    }

    private static AlertDialog.Builder message(Activity activity, Theme.ResourcesProvider resourcesProvider, String title, String text) {
        final AlertDialog.Builder builder = new AlertDialog.Builder(activity, resourcesProvider);
        builder.setTitle(title);
        builder.setMessage(text);
        builder.setPositiveButton(getString(R.string.OK), null);
        return builder;
    }

    private static AlertDialog showProgress(Activity activity, Theme.ResourcesProvider resourcesProvider, String text) {
        try {
            final AlertDialog dialog = new AlertDialog(activity, AlertDialog.ALERT_TYPE_SPINNER, resourcesProvider);
            dialog.setMessage(text);
            dialog.setCanCancel(false);
            dialog.show();
            return dialog;
        } catch (Exception e) {
            FileLog.e(e);
            return null;
        }
    }

    // A plain window with text: the first translation downloads the language files, so it can take a while
    private static AlertDialog showWaitMessage(Activity activity, Theme.ResourcesProvider resourcesProvider, String title, String text) {
        try {
            final AlertDialog.Builder builder = new AlertDialog.Builder(activity, resourcesProvider);
            builder.setTitle(title);
            builder.setMessage(text);
            final AlertDialog dialog = builder.create();
            dialog.setCanceledOnTouchOutside(false);
            dialog.show();
            return dialog;
        } catch (Exception e) {
            FileLog.e(e);
            return null;
        }
    }

    private static void dismiss(AlertDialog dialog) {
        if (dialog == null) {
            return;
        }
        try {
            dialog.dismiss();
        } catch (Exception e) {
            FileLog.e(e);
        }
    }
}
