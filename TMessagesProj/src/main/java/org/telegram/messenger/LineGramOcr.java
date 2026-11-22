package org.telegram.messenger;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.text.TextUtils;

import com.googlecode.tesseract.android.TessBaseAPI;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * LineGram: reads the text in a photo on the phone itself, with no internet.
 * Uses Tesseract with the Arabic and English models shipped in assets/tessdata.
 */
public class LineGramOcr {

    public interface Callback {
        /** The text found, "" when the photo has none, or null when reading failed. */
        void run(String text);
    }

    private static final String[] LANGUAGES = {"ara", "eng"};
    private static final int MAX_SIDE = 2400;
    private static final int PAGE_SEG_MODE_AUTO = 3; // Tesseract's PSM_AUTO: finds the text blocks by itself

    private static DispatchQueue queue;

    public static void recognize(String imagePath, Callback callback) {
        if (queue == null) {
            queue = new DispatchQueue("LineGramOcr");
        }
        queue.postRunnable(() -> {
            String text = null;
            try {
                text = recognizeSync(imagePath);
            } catch (Throwable e) {
                FileLog.e(e);
            }
            final String result = text;
            AndroidUtilities.runOnUIThread(() -> {
                if (callback != null) {
                    callback.run(result);
                }
            });
        });
    }

    private static String recognizeSync(String imagePath) throws Exception {
        if (TextUtils.isEmpty(imagePath) || !new File(imagePath).exists()) {
            return null;
        }
        final File root = prepareModels();
        if (root == null) {
            return null;
        }
        final Bitmap bitmap = decode(imagePath);
        if (bitmap == null) {
            return null;
        }
        final TessBaseAPI api = new TessBaseAPI();
        try {
            if (!api.init(root.getAbsolutePath(), TextUtils.join("+", LANGUAGES))) {
                return null;
            }
            api.setPageSegMode(PAGE_SEG_MODE_AUTO);
            api.setImage(bitmap);
            final String text = api.getUTF8Text();
            return clean(text);
        } finally {
            try {
                api.recycle();
            } catch (Throwable ignore) {
            }
            bitmap.recycle();
        }
    }

    /** Copies the language models from the app's assets to a folder Tesseract can read, once. */
    private static File prepareModels() {
        final File root = new File(ApplicationLoader.getFilesDirFixed(), "linegram_ocr");
        final File tessdata = new File(root, "tessdata");
        if (!tessdata.isDirectory() && !tessdata.mkdirs()) {
            return null;
        }
        for (String language : LANGUAGES) {
            final File model = new File(tessdata, language + ".traineddata");
            if (model.exists() && model.length() > 0) {
                continue;
            }
            final File temp = new File(tessdata, language + ".traineddata.tmp");
            try (InputStream in = ApplicationLoader.applicationContext.getAssets().open("tessdata/" + language + ".traineddata");
                 OutputStream out = new FileOutputStream(temp)) {
                final byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = in.read(buffer)) != -1) {
                    out.write(buffer, 0, read);
                }
            } catch (Exception e) {
                FileLog.e(e);
                temp.delete();
                return null;
            }
            if (!temp.renameTo(model)) {
                temp.delete();
                return null;
            }
        }
        return root;
    }

    private static Bitmap decode(String path) {
        final BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(path, bounds);
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            return null;
        }
        int sample = 1;
        while (Math.max(bounds.outWidth, bounds.outHeight) / sample > MAX_SIDE) {
            sample *= 2;
        }
        final BitmapFactory.Options options = new BitmapFactory.Options();
        options.inSampleSize = sample;
        options.inPreferredConfig = Bitmap.Config.ARGB_8888;
        final Bitmap bitmap = BitmapFactory.decodeFile(path, options);
        if (bitmap == null) {
            return null;
        }
        if (bitmap.getConfig() != Bitmap.Config.ARGB_8888) {
            final Bitmap copy = bitmap.copy(Bitmap.Config.ARGB_8888, false);
            bitmap.recycle();
            return copy;
        }
        return bitmap;
    }

    private static String clean(String text) {
        if (text == null) {
            return "";
        }
        // Tesseract marks direction with invisible LRM/RLM characters; they only get in the way when pasting
        return text.replace("‎", "").replace("‏", "").trim();
    }
}
