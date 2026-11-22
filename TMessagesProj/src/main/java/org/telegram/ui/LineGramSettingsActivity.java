package org.telegram.ui;

import static org.telegram.messenger.LocaleController.getString;

import android.content.Context;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;

import androidx.annotation.Nullable;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LineGramConfig;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.Cells.AppIconsSelectorCell;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Components.BulletinFactory;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Components.RecyclerListView;
import org.telegram.ui.Components.UItem;
import org.telegram.ui.Components.UniversalAdapter;
import org.telegram.ui.Components.UniversalRecyclerView;

import java.util.ArrayList;

/** LineGram: one screen for all of the app's own features. */
public class LineGramSettingsActivity extends BaseFragment {

    private static final int ID_CONFIRM_VOICE = 1;
    private static final int ID_CONFIRM_STICKER = 2;
    private static final int ID_CONFIRM_GIF = 3;
    private static final int ID_HIDE_STORIES = 4;
    private static final int ID_HIDE_PREMIUM = 5;
    private static final int ID_SHOW_ID = 6;
    private static final int ID_TIME_SECONDS = 7;
    private static final int ID_FULL_DATE = 8;
    private static final int ID_HIDE_PHONE = 9;
    private static final int ID_YOUR_ID = 10;
    private static final int ID_SAVE_FOLDER = 11;

    private UniversalRecyclerView listView;
    private AppIconsSelectorCell appIconsCell;

    @Override
    protected boolean useSimpleActionBar() {
        return true;
    }

    @Override
    public View createView(Context context) {
        setHasOwnBackground(true);
        simpleActionBar.setBackButtonImage(R.drawable.ic_ab_back);
        simpleActionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });
        simpleActionBar.setTitle(getString(R.string.LineGramSettings));

        final FrameLayout contentView = new FrameLayout(context);

        appIconsCell = new AppIconsSelectorCell(context, this, currentAccount);

        listView = new UniversalRecyclerView(this, this::fillItems, this::onItemClick, null);
        listView.setSections();
        listView.setSectionsDrawBackground(true);
        contentView.addView(listView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT, Gravity.FILL));

        return fragmentView = contentView;
    }

    private void fillItems(ArrayList<UItem> items, UniversalAdapter adapter) {
        if (appIconsCell != null) {
            items.add(UItem.asHeader(getString(R.string.LineGramHeaderIcon)));
            final UItem iconsItem = UItem.asCustom(appIconsCell);
            iconsItem.intValue = LayoutHelper.WRAP_CONTENT;
            items.add(iconsItem);
            items.add(UItem.asShadow(getString(R.string.LineGramIconInfo)));
        }

        items.add(UItem.asHeader(getString(R.string.LineGramHeaderSending)));
        items.add(UItem.asCheck(ID_CONFIRM_VOICE, getString(R.string.LineGramConfirmVoice)).setChecked(LineGramConfig.confirmVoice()));
        items.add(UItem.asCheck(ID_CONFIRM_STICKER, getString(R.string.LineGramConfirmSticker)).setChecked(LineGramConfig.confirmSticker()));
        items.add(UItem.asCheck(ID_CONFIRM_GIF, getString(R.string.LineGramConfirmGif)).setChecked(LineGramConfig.confirmGif()));
        items.add(UItem.asShadow(getString(R.string.LineGramConfirmInfo)));

        items.add(UItem.asHeader(getString(R.string.LineGramHeaderInterface)));
        items.add(UItem.asCheck(ID_HIDE_STORIES, getString(R.string.LineGramHideStories)).setChecked(LineGramConfig.hideStories()));
        items.add(UItem.asCheck(ID_HIDE_PREMIUM, getString(R.string.LineGramHidePremium)).setChecked(LineGramConfig.hidePremium()));
        items.add(UItem.asCheck(ID_SHOW_ID, getString(R.string.LineGramShowId)).setChecked(LineGramConfig.showId()));
        items.add(UItem.asCheck(ID_TIME_SECONDS, getString(R.string.LineGramTimeSeconds)).setChecked(LineGramConfig.timeSeconds()));
        items.add(UItem.asCheck(ID_FULL_DATE, getString(R.string.LineGramFullDate)).setChecked(LineGramConfig.fullDate()));
        items.add(UItem.asShadow(getString(R.string.LineGramInterfaceInfo)));

        items.add(UItem.asHeader(getString(R.string.LineGramHeaderPrivacy)));
        items.add(UItem.asCheck(ID_HIDE_PHONE, getString(R.string.LineGramHidePhone)).setChecked(LineGramConfig.hidePhone()));
        items.add(UItem.asButton(ID_YOUR_ID, R.drawable.msg_copy, getString(R.string.LineGramYourId), String.valueOf(getUserConfig().getClientUserId())));
        items.add(UItem.asShadow(null));

        items.add(UItem.asHeader(getString(R.string.LineGramHeaderStorage)));
        items.add(UItem.asButton(ID_SAVE_FOLDER, R.drawable.msg_folders, getString(R.string.LineGramSaveFolder), LineGramConfig.FOLDER));
        items.add(UItem.asShadow(getString(R.string.LineGramSaveFolderInfo)));
    }

    private void onItemClick(UItem item, View view, int position, float x, float y) {
        final String key;
        switch (item.id) {
            case ID_CONFIRM_VOICE: key = LineGramConfig.KEY_CONFIRM_VOICE; break;
            case ID_CONFIRM_STICKER: key = LineGramConfig.KEY_CONFIRM_STICKER; break;
            case ID_CONFIRM_GIF: key = LineGramConfig.KEY_CONFIRM_GIF; break;
            case ID_HIDE_STORIES: key = LineGramConfig.KEY_HIDE_STORIES; break;
            case ID_HIDE_PREMIUM: key = LineGramConfig.KEY_HIDE_PREMIUM; break;
            case ID_SHOW_ID: key = LineGramConfig.KEY_SHOW_ID; break;
            case ID_TIME_SECONDS: key = LineGramConfig.KEY_TIME_SECONDS; break;
            case ID_FULL_DATE: key = LineGramConfig.KEY_FULL_DATE; break;
            case ID_HIDE_PHONE: key = LineGramConfig.KEY_HIDE_PHONE; break;
            case ID_YOUR_ID: {
                if (AndroidUtilities.addToClipboard(String.valueOf(getUserConfig().getClientUserId()))) {
                    BulletinFactory.of(this).createCopyBulletin(getString(R.string.LineGramIdCopied)).show();
                }
                return;
            }
            default:
                return;
        }
        final boolean value = LineGramConfig.toggle(key);
        if (view instanceof TextCheckCell) {
            ((TextCheckCell) view).setChecked(value);
        }
        if (listView != null && listView.adapter != null) {
            listView.adapter.update(true);
        }
    }

    @Override
    public boolean isSupportEdgeToEdge() {
        return true;
    }

    @Nullable
    @Override
    protected RecyclerListView getListViewForSimpleGlass() {
        return listView;
    }
}
