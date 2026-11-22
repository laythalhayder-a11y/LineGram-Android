package org.telegram.ui;

import static org.telegram.messenger.LocaleController.formatString;
import static org.telegram.messenger.LocaleController.getString;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.pdf.PdfDocument;
import android.net.Uri;
import android.os.Build;
import android.text.Layout;
import android.text.StaticLayout;
import android.text.TextDirectionHeuristics;
import android.text.TextPaint;
import android.text.TextUtils;

import androidx.core.content.FileProvider;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.FileLoader;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.MediaController;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.MessagesController;
import org.telegram.messenger.R;
import org.telegram.messenger.UserConfig;
import org.telegram.messenger.UserObject;
import org.telegram.messenger.Utilities;
import org.telegram.tgnet.ConnectionsManager;
import org.telegram.tgnet.TLRPC;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.Components.BulletinFactory;

import java.io.File;
import java.io.FileOutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.Locale;

/**
 * LineGram: saves a whole chat as a PDF file. The history is read page by page from
 * Telegram's servers (up to MAX_MESSAGES), then drawn with Android's own PDF writer.
 * Media are written as labels such as [Photo]; their captions are kept.
 */
public class LineGramChatExporter {

    private static final int MAX_MESSAGES = 10000;
    private static final int PAGE_SIZE = 100;

    // A4 in PostScript points
    private static final int PAGE_WIDTH = 595;
    private static final int PAGE_HEIGHT = 842;
    private static final int MARGIN = 40;
    private static final int FOOTER_SPACE = 24;

    private final BaseFragment fragment;
    private final int account;
    private final long dialogId;
    private final String title;
    private final ArrayList<String[]> rows = new ArrayList<>(); // {sender and time, text}, newest first
    private final SimpleDateFormat rowDate = new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US);

    private TLRPC.InputPeer peer;
    private AlertDialog progress;
    private boolean cancelled;
    private int total;

    public static void start(BaseFragment fragment, long dialogId, String title) {
        if (fragment == null || fragment.getParentActivity() == null) {
            return;
        }
        new LineGramChatExporter(fragment, dialogId, title).begin();
    }

    private LineGramChatExporter(BaseFragment fragment, long dialogId, String title) {
        this.fragment = fragment;
        this.account = fragment.getCurrentAccount();
        this.dialogId = dialogId;
        this.title = TextUtils.isEmpty(title) ? "LineGram" : title;
    }

    private void begin() {
        peer = MessagesController.getInstance(account).getInputPeer(dialogId);
        if (peer == null) {
            showMessage(getString(R.string.LineGramExportFailed));
            return;
        }
        try {
            progress = new AlertDialog(fragment.getParentActivity(), AlertDialog.ALERT_TYPE_LOADING, fragment.getResourceProvider());
            progress.setMessage(formatString(R.string.LineGramExportProgress, 0));
            progress.setCanceledOnTouchOutside(false);
            progress.setCancelable(true);
            progress.setOnCancelListener(d -> cancelled = true);
            progress.show();
        } catch (Exception e) {
            FileLog.e(e);
        }
        loadPage(0, 0);
    }

    private void loadPage(int offsetId, int attempt) {
        if (cancelled) {
            return;
        }
        final TLRPC.TL_messages_getHistory req = new TLRPC.TL_messages_getHistory();
        req.peer = peer;
        req.offset_id = offsetId;
        req.limit = PAGE_SIZE;
        ConnectionsManager.getInstance(account).sendRequest(req, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            if (cancelled) {
                return;
            }
            if (error != null || !(response instanceof TLRPC.messages_Messages)) {
                if (error != null && error.text != null && error.text.startsWith("FLOOD_WAIT_") && attempt < 3) {
                    final Integer seconds = Utilities.parseInt(error.text);
                    final int wait = Math.min(30, Math.max(1, seconds == null ? 5 : seconds));
                    AndroidUtilities.runOnUIThread(() -> loadPage(offsetId, attempt + 1), wait * 1000L);
                } else if (rows.isEmpty()) {
                    dismissProgress();
                    showMessage(getString(R.string.LineGramExportFailed));
                } else {
                    buildPdf(true);
                }
                return;
            }
            final TLRPC.messages_Messages res = (TLRPC.messages_Messages) response;
            final MessagesController controller = MessagesController.getInstance(account);
            controller.putUsers(res.users, false);
            controller.putChats(res.chats, false);
            if (res.count > 0) {
                total = Math.min(res.count, MAX_MESSAGES);
            }
            final boolean wholeHistory = res instanceof TLRPC.TL_messages_messages;
            final ArrayList<TLRPC.Message> messages = new ArrayList<>(res.messages);
            Utilities.globalQueue.postRunnable(() -> {
                final ArrayList<String[]> page = new ArrayList<>();
                int lowestId = Integer.MAX_VALUE;
                for (TLRPC.Message message : messages) {
                    if (message == null || message instanceof TLRPC.TL_messageEmpty) {
                        continue;
                    }
                    lowestId = Math.min(lowestId, message.id);
                    try {
                        page.add(formatRow(message));
                    } catch (Throwable e) {
                        FileLog.e(e);
                    }
                }
                final int nextOffset = lowestId;
                AndroidUtilities.runOnUIThread(() -> {
                    if (cancelled) {
                        return;
                    }
                    rows.addAll(page);
                    updateProgress();
                    final boolean reachedEnd = wholeHistory || messages.isEmpty() || nextOffset == Integer.MAX_VALUE || nextOffset <= 1;
                    if (rows.size() >= MAX_MESSAGES) {
                        buildPdf(true);
                    } else if (reachedEnd) {
                        buildPdf(false);
                    } else {
                        loadPage(nextOffset, 0);
                    }
                });
            });
        }));
    }

    private String[] formatRow(TLRPC.Message message) {
        final MessageObject object = new MessageObject(account, message, false, false);
        final MessagesController controller = MessagesController.getInstance(account);

        String sender;
        if (message.out) {
            sender = UserObject.getUserName(UserConfig.getInstance(account).getCurrentUser());
        } else {
            final long fromId = object.getFromChatId();
            if (fromId > 0) {
                sender = UserObject.getUserName(controller.getUser(fromId));
            } else {
                final TLRPC.Chat chat = controller.getChat(-fromId);
                sender = chat != null ? chat.title : "";
            }
        }
        final String header = (TextUtils.isEmpty(sender) ? "" : sender + "  •  ") + rowDate.format(new Date((long) message.date * 1000L));

        String text;
        if (message instanceof TLRPC.TL_messageService) {
            text = object.messageText != null ? object.messageText.toString() : "";
        } else {
            final boolean hasMedia = message.media != null
                    && !(message.media instanceof TLRPC.TL_messageMediaEmpty)
                    && !(message.media instanceof TLRPC.TL_messageMediaWebPage);
            if (hasMedia) {
                final StringBuilder sb = new StringBuilder();
                sb.append('[').append(object.messageText != null ? object.messageText.toString() : "").append(']');
                final TLRPC.Document document = object.getDocument();
                if (document != null && !object.isVoice() && !object.isRoundVideo() && !object.isSticker() && !object.isAnimatedSticker() && !object.isGif() && !object.isVideo() && !object.isMusic()) {
                    final String fileName = FileLoader.getDocumentFileName(document);
                    if (!TextUtils.isEmpty(fileName)) {
                        sb.append(' ').append(fileName);
                    }
                }
                if (!TextUtils.isEmpty(message.message)) {
                    sb.append('\n').append(message.message);
                }
                text = sb.toString();
            } else {
                text = message.message != null ? message.message : "";
            }
        }
        return new String[] {header, text};
    }

    private void updateProgress() {
        if (progress == null) {
            return;
        }
        progress.setMessage(formatString(R.string.LineGramExportProgress, rows.size()));
        if (total > 0) {
            progress.setProgress(Math.min(99, rows.size() * 100 / total));
        }
    }

    private void buildPdf(boolean limited) {
        if (rows.isEmpty()) {
            dismissProgress();
            showMessage(getString(R.string.LineGramExportEmpty));
            return;
        }
        if (progress != null) {
            progress.setMessage(getString(R.string.LineGramExportBuilding));
            progress.setProgress(99);
        }
        final ArrayList<String[]> list = new ArrayList<>(rows);
        Collections.reverse(list); // oldest first, like reading the chat
        Utilities.globalQueue.postRunnable(() -> {
            File file = null;
            try {
                file = writePdf(list);
            } catch (Throwable e) {
                FileLog.e(e);
            }
            final File result = file;
            AndroidUtilities.runOnUIThread(() -> {
                dismissProgress();
                if (cancelled) {
                    return;
                }
                if (result == null) {
                    showMessage(getString(R.string.LineGramExportFailed));
                } else {
                    showDone(result, list.size(), limited);
                }
            });
        });
    }

    // ---- drawing ------------------------------------------------------------

    private PdfDocument document;
    private PdfDocument.Page page;
    private Canvas canvas;
    private int pageNumber;
    private float y;
    private TextPaint footerPaint;

    private File writePdf(ArrayList<String[]> list) throws Exception {
        File dir = ApplicationLoader.applicationContext.getExternalCacheDir();
        if (dir == null) {
            dir = new File(ApplicationLoader.applicationContext.getFilesDir(), "cache");
        }
        dir = new File(dir, "linegram_export");
        if (!dir.isDirectory() && !dir.mkdirs()) {
            return null;
        }
        String safeTitle = title.replaceAll("[\\\\/:*?\"<>|\\r\\n\\t]", "_").trim();
        if (safeTitle.length() > 40) {
            safeTitle = safeTitle.substring(0, 40);
        }
        final String stamp = new SimpleDateFormat("yyyy-MM-dd_HH-mm", Locale.US).format(new Date());
        final File out = new File(dir, "LineGram_" + safeTitle + "_" + stamp + ".pdf");

        Typeface regular = AndroidUtilities.getTypeface("fonts/lg_cairo.ttf");
        if (regular == null) {
            regular = Typeface.DEFAULT;
        }
        final Typeface bold = Typeface.create(regular, Typeface.BOLD);

        final TextPaint titlePaint = paint(bold, 18, 0xFF111111);
        final TextPaint metaPaint = paint(regular, 9, 0xFF808080);
        final TextPaint namePaint = paint(bold, 9.5f, 0xFFE0621F);
        final TextPaint bodyPaint = paint(regular, 11, 0xFF1E1E1E);
        footerPaint = paint(regular, 8, 0xFF9A9A9A);
        final Paint linePaint = new Paint();
        linePaint.setColor(0xFFF96B33);
        linePaint.setStrokeWidth(1.2f);

        final int width = PAGE_WIDTH - MARGIN * 2;
        document = new PdfDocument();
        pageNumber = 0;
        newPage();

        drawLayout(layout(title, titlePaint, width));
        y += 4;
        final String exportedOn = new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(new Date());
        drawLayout(layout(formatString(R.string.LineGramExportHeader, exportedOn, list.size()), metaPaint, width));
        y += 8;
        canvas.drawLine(MARGIN, y, PAGE_WIDTH - MARGIN, y, linePaint);
        y += 14;

        for (String[] row : list) {
            drawLayout(layout(row[0], namePaint, width));
            y += 1;
            drawLayout(layout(TextUtils.isEmpty(row[1]) ? " " : row[1], bodyPaint, width));
            y += 10;
        }
        finishPage();

        try (FileOutputStream stream = new FileOutputStream(out)) {
            document.writeTo(stream);
        } finally {
            document.close();
            document = null;
        }
        return out;
    }

    private static TextPaint paint(Typeface typeface, float size, int color) {
        final TextPaint paint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
        paint.setTypeface(typeface);
        paint.setTextSize(size);
        paint.setColor(color);
        return paint;
    }

    private static StaticLayout layout(CharSequence text, TextPaint paint, int width) {
        return StaticLayout.Builder.obtain(text, 0, text.length(), paint, width)
                .setAlignment(Layout.Alignment.ALIGN_NORMAL)
                .setTextDirection(TextDirectionHeuristics.FIRSTSTRONG_LTR) // Arabic lines start on the right
                .setLineSpacing(0, 1.12f)
                .setIncludePad(false)
                .build();
    }

    /** Draws a text block line by line, so a long message can continue on the next page. */
    private void drawLayout(StaticLayout layout) {
        final int bottomLimit = PAGE_HEIGHT - MARGIN - FOOTER_SPACE;
        for (int line = 0; line < layout.getLineCount(); line++) {
            final int top = layout.getLineTop(line);
            final int bottom = layout.getLineBottom(line);
            if (y + (bottom - top) > bottomLimit) {
                finishPage();
                newPage();
            }
            canvas.save();
            canvas.translate(MARGIN, y - top);
            canvas.clipRect(0, top, layout.getWidth(), bottom);
            layout.draw(canvas);
            canvas.restore();
            y += bottom - top;
        }
    }

    private void newPage() {
        pageNumber++;
        final PdfDocument.PageInfo info = new PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber).create();
        page = document.startPage(info);
        canvas = page.getCanvas();
        y = MARGIN;
    }

    private void finishPage() {
        if (page == null) {
            return;
        }
        final String footer = "LineGram  •  " + formatString(R.string.LineGramExportPage, pageNumber);
        final float textWidth = footerPaint.measureText(footer);
        canvas.drawText(footer, (PAGE_WIDTH - textWidth) / 2f, PAGE_HEIGHT - MARGIN + 6, footerPaint);
        document.finishPage(page);
        page = null;
        canvas = null;
    }

    // ---- result -------------------------------------------------------------

    private void showDone(File file, int count, boolean limited) {
        final Activity activity = fragment.getParentActivity();
        if (activity == null) {
            return;
        }
        String message = formatString(R.string.LineGramExportDone, count);
        if (limited) {
            message += "\n" + formatString(R.string.LineGramExportLimit, count);
        }
        final AlertDialog.Builder builder = new AlertDialog.Builder(activity, fragment.getResourceProvider());
        builder.setTitle(getString(R.string.LineGramExportPdf));
        builder.setMessage(message);
        builder.setPositiveButton(getString(R.string.LineGramExportShare), (dialog, which) -> share(activity, file));
        builder.setNeutralButton(getString(R.string.LineGramExportSave), (dialog, which) -> saveToDownloads(activity, file));
        builder.setNegativeButton(getString(R.string.Close), null);
        fragment.showDialog(builder.create());
    }

    private void share(Activity activity, File file) {
        try {
            final Uri uri = FileProvider.getUriForFile(activity, ApplicationLoader.getApplicationId() + ".provider", file);
            final Intent intent = new Intent(Intent.ACTION_SEND);
            intent.setType("application/pdf");
            intent.putExtra(Intent.EXTRA_STREAM, uri);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            activity.startActivity(Intent.createChooser(intent, getString(R.string.LineGramExportShare)));
        } catch (Exception e) {
            FileLog.e(e);
            showMessage(getString(R.string.LineGramExportFailed));
        }
    }

    private void saveToDownloads(Activity activity, File file) {
        if (Build.VERSION.SDK_INT >= 23 && Build.VERSION.SDK_INT <= 28
                && activity.checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            activity.requestPermissions(new String[] {Manifest.permission.WRITE_EXTERNAL_STORAGE}, 4);
            showMessage(getString(R.string.LineGramExportNeedStorage));
            return;
        }
        MediaController.saveFile(file.getAbsolutePath(), activity, 2, file.getName(), "application/pdf", uri ->
                BulletinFactory.of(fragment).createSimpleBulletin(R.raw.done, getString(R.string.LineGramExportSaved)).show());
    }

    private void showMessage(String text) {
        final Activity activity = fragment.getParentActivity();
        if (activity == null) {
            return;
        }
        final AlertDialog.Builder builder = new AlertDialog.Builder(activity, fragment.getResourceProvider());
        builder.setTitle(getString(R.string.LineGramExportPdf));
        builder.setMessage(text);
        builder.setPositiveButton(getString(R.string.OK), null);
        fragment.showDialog(builder.create());
    }

    private void dismissProgress() {
        if (progress != null) {
            try {
                progress.dismiss();
            } catch (Exception e) {
                FileLog.e(e);
            }
            progress = null;
        }
    }
}
