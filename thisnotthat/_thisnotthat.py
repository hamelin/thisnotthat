from anywidget import AnyWidget
from collections.abc import Hashable, Mapping
import glasbey
import ipywidgets as wg
from jscatter import Scatter
from matplotlib.colors import to_rgba
import pandas as pd
from pathlib import Path
import traitlets as tl
from typing import Any
import numpy as np

import quak

NAME_UNLABELLED = "<Unlabelled>"
Categorical = Hashable
Label = str
Tag = str
SEARCH_HIGHLIGHT_COLOR = "#FFD700"  # gold

def is_value_unlabelled(label: Label) -> bool:
    return str(label).lower() in {
        '', 'nan', 'none', '-1', '-1.0', 'false', NAME_UNLABELLED.lower()
    }


def normalize_categorical(value: Any) -> Label:
    if is_value_unlabelled(value):
        return NAME_UNLABELLED
    return Label(value)


Color = str
Palette = list[Color]
ColorMap = Mapping[Categorical, Color]
COLOR_UNLABELLED = "#cccccc"
PALETTE_DEFAULT = glasbey.extend_palette([COLOR_UNLABELLED])


class LabelEditor(AnyWidget):

    labels = tl.List().tag(sync=True)
    categories = tl.List().tag(sync=True)
    palette = tl.List(default_value=[]).tag(sync=True)
    size_font = tl.Int(default_value=12).tag(sync=True)
    width_color_bar = tl.Int(default_value=30).tag(sync=True)
    space_color_bar_info = tl.Int(default_value=5).tag(sync=True)
    selection = tl.List(default_value=[]).tag(sync=True)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.palette:
            # self.palette = glasbey.extend_palette([self.color_uncat], 257)[1:]
            self.palette = [
                to_rgba(c)
                for c in glasbey.extend_palette([to_rgba(COLOR_UNLABELLED)], 256)
            ]


class CategoricalEditor(LabelEditor):

    _esm = Path(__file__).parent / "js" / "legend" / "categorical.js"
    _css = Path(__file__).parent / "css" / "legend" / "categorical.css"

    min_height_item = tl.Int(default_value=24).tag(sync=True)


class TopBar(AnyWidget):
    _esm = Path(__file__).parent / "js" / "topbar.js"
    _css = Path(__file__).parent / "css" / "topbar.css"


class TagWidget(AnyWidget):
    tags = tl.List(trait=tl.Set()).tag(sync=True)
    tag_set = tl.List(trait=tl.Dict()).tag(sync=True)
    tag_int_id = tl.Int(default_value=0).tag(sync=True)
    tag_to_int = tl.Dict(default_value={}).tag(sync=True)
    int_to_tag = tl.Dict(default_value={}).tag(sync=True)
    selection = tl.List(default_value=[]).tag(sync=True)
    num_points = tl.Int(default_value=0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_initial_tag_set()
        if not self.tags:
            self.tags = [set() for _ in range(self.num_points)]

        self._update_tag_mapping()
        self.tags = [self._map_tags_to_int(t) for t in self.tags]

        self.observe(self._on_state_change, names=["tag_set"])
        self.on_msg(self._handle_js_message)

    def get_initial_tag_set(self):
        """
        Initialise tag_set from self.tags content. Sort alphabetically.
        """
        if self.tags:
            tag_set_tmp = set()
            for s in self.tags:
                tag_set_tmp.update(s)
            sorted_tags = sorted(list(tag_set_tmp), key=str.lower)
        else:
            sorted_tags = []
        self.tag_set = [
            {"tag_id": idx, "tag": tag, "include_btn_active": False, "exclude_btn_active": False}
            for idx, tag in enumerate(sorted_tags)
        ]

    def _update_tag_mapping(self):
        """
        Completely rebuild the name ↔ int mapping to avoid stale mappings on rename.
        """
        self.tag_to_int.clear()
        self.int_to_tag.clear()
        self.tag_int_id = 0
        for tag_dict in sorted(self.tag_set, key=lambda t: t["tag"].lower()):
            tag_name = tag_dict["tag"]
            if tag_name not in self.tag_to_int:
                self.tag_to_int[tag_name] = tag_dict["tag_id"]
                self.int_to_tag[tag_dict["tag_id"]] = tag_name
                # Ensure tag_int_id stays > largest existing
                self.tag_int_id = max(self.tag_int_id, tag_dict["tag_id"] + 1)

    def _map_tags_to_int(self, point_tags):
        return set([self.tag_to_int[t] for t in point_tags if t in self.tag_to_int])

    def _on_state_change(self, change):
        """
        Called when tag_set changes in frontend.
        """
        self._update_tag_mapping()
        self.calculate_selection()

    def calculate_selection(self):
        """
        Determine the selection based on include/exclude flags in tag_set.
        """
        include_buttons_checked = {t["tag_id"] for t in self.tag_set if t["include_btn_active"]}
        exclude_buttons_checked = {t["tag_id"] for t in self.tag_set if t["exclude_btn_active"]}

        to_select = np.where([include_buttons_checked.issubset(s) for s in self.tags])[0]
        to_remove = np.where([bool(exclude_buttons_checked.intersection(s)) for s in self.tags])[0]

        new_selection = np.setdiff1d(to_select, to_remove).tolist()

        if not (include_buttons_checked or exclude_buttons_checked):
            new_selection = []

        self.selection = list(new_selection)
        self.send_state()

    def add_tag_to_selected(self, tag_name, assign=True, auto_include=False):
        """
        Ensure tag exists and optionally assign to selected points.
        """
        self._update_tag_mapping()
        if tag_name not in self.tag_to_int:
            tag_id_int = self.tag_int_id
            self.tag_to_int[tag_name] = tag_id_int
            self.int_to_tag[tag_id_int] = tag_name
            self.tag_int_id += 1
            self.tag_set.append({
                "tag_id": tag_id_int,
                "tag": tag_name,
                "include_btn_active": False,
                "exclude_btn_active": False
            })
        tag_id_int = self.tag_to_int[tag_name]

        if assign and self.selection:
            for idx in self.selection:
                self.tags[idx].add(tag_id_int)

        # Auto-include behaviour
        if auto_include:
            for t in self.tag_set:
                if t["tag_id"] == tag_id_int:
                    t["include_btn_active"] = True

        # Rebuild to sync IDs properly
        synced_tag_set = []
        for name, tag_id in self.tag_to_int.items():
            active = next((t for t in self.tag_set if t["tag"] == name), None)
            synced_tag_set.append({
                "tag_id": tag_id,
                "tag": name,
                "include_btn_active": active["include_btn_active"] if active else False,
                "exclude_btn_active": active["exclude_btn_active"] if active else False
            })
        self.tag_set = list(synced_tag_set)

        self.tags = list(self.tags)
        self.calculate_selection()
        # Ensure immediate front‑end sync
        self.selection = list(self.selection)
        self.send_state()

    def remove_tag_from_selected(self, tag_name, auto_include=False):
        """
        Remove a tag from all selected points (if it exists on them).
        """
        self._update_tag_mapping()
        if tag_name not in self.tag_to_int:
            return
        tag_id_int = self.tag_to_int[tag_name]
        for idx in self.selection:
            if tag_id_int in self.tags[idx]:
                self.tags[idx].remove(tag_id_int)

        if auto_include:
            for t in self.tag_set:
                if t["tag_id"] == tag_id_int:
                    t["include_btn_active"] = True

        self.tags = list(self.tags)
        self.calculate_selection()
        self.send_state()

    def export_tags(self):
        """Export the tags for each data point as a list of lists of tag strings."""        
        tag_strings_for_points = []
        for point_tags in self.tags:
            tag_names = [self.int_to_tag[tag_id] for tag_id in sorted(point_tags)]
            tag_strings_for_points.append(tag_names)
        return tag_strings_for_points

    def _handle_js_message(self, _, content, buffers):
        """Handle messages from JS."""
        action = content.get("action")
        if action == "assign_tag_to_selection":
            tag_id = content.get("tag_id")
            tag = content.get("tag")
            assign = content.get("assign", True)
            auto_include = content.get("auto_include", False)
            indices = content.get("assign_indices", [])
            if indices:
                self.selection = [int(i) for i in indices]
            if tag_id is not None and tag_id in self.int_to_tag:
                tag = self.int_to_tag[tag_id]
            self.add_tag_to_selected(tag, assign, auto_include)
            self.send_state()

        elif action == "remove_tag_from_selection":
            tag_id = content.get("tag_id")
            tag = content.get("tag")
            auto_include = content.get("auto_include", False)
            if tag_id is not None and tag_id in self.int_to_tag:
                tag = self.int_to_tag[tag_id]
            self.remove_tag_from_selected(tag, auto_include)



class TagEditor(TagWidget):
    _esm = Path(__file__).parent / "js" / "legend" / "tag_editor.js"
    _css = Path(__file__).parent / "css" / "legend" / "tag_editor.css"

    min_height_item = tl.Int(default_value=24).tag(sync=True)


class TopBar(AnyWidget):
    _esm = Path(__file__).parent / "js" / "topbar.js"
    _css = Path(__file__).parent / "css" / "topbar.css"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_msg(self._handle_js_message)
        # Will be set by dashboard
        self._on_search = None

    def _handle_js_message(self, _, content, buffers):
        action = content.get("action")
        if action == "search":
            query = content.get("query", "").strip()
            if callable(self._on_search):
                self._on_search(query)

    def clear_search(self):
        # Reset search widget if scatterplot selection resets
        self.send({"action": "clear_search"})

class Dashboard:
    def __init__(
        self,
        data: pd.DataFrame,
        labels: str | list[Label] | dict[Hashable, Label] | pd.Series | None,
        tags: str | list[Tag] | dict[Hashable, Tag] | pd.Series = [],
        height: int = 400,
        search_columns: list[str] | None = None,
        hover_column: str | None = None,
        content_renderer = None
    ) -> None:
        self._data = data
        self._height = height
        self._content_renderer = content_renderer
        self._quak_container = wg.Box(layout=wg.Layout(
                # display="flex",
                # flex_flow="row wrap",
                # align_items="stretch",
                # align_content="stretch",
                # height=f"{self._height + 25}px",
                # flex="1 1 auto",
                width="100%",
            ))
        self._quak_container.children = [quak.Widget(self._data.iloc[[]])]

        if search_columns is not None:
            self._search_columns = search_columns
        else:
            self._search_columns = ["text"]

        if isinstance(labels, str):
            dict_labels = self._data[labels].to_dict()
        else:
            raise NotImplementedError()

        column_x = "x"
        column_y = "y"

        self._topbar = TopBar()

        labels_normalized = pd.Series(
            {k: normalize_categorical(v) for k, v in dict_labels.items()},
            index=self._data.index
        ).fillna(NAME_UNLABELLED).to_list()

        self._editor = CategoricalEditor(
            labels=labels_normalized,
            categories=[
                NAME_UNLABELLED,
                *sorted(set(labels_normalized) - {NAME_UNLABELLED})
            ],
        )


        self._scatter = Scatter(
            data=self._data.join(
                self.labels(name="__labels__"),
                how="left",
            ),
            x=column_x,
            y=column_y,
            color_by="__labels__",
            color_map=self._editor.palette,
            height=self._height,
        )

        if hover_column is not None:
            self._scatter.tooltip(enable=True, properties=hover_column, preview=hover_column)

        self._scatter.widget.color = self._editor.palette
        self._tag_editor = TagEditor(tags=tags, num_points=len(self._data))

        # Create the content pane now (empty initially)
        self._content_pane = wg.Output()
        with self._content_pane:
            print("Select points to view details here.")

        def on_color_change(_change):
            self._scatter.color(map=self._editor.palette)
            self._scatter.widget.color = self._editor.palette
        self._editor.observe(on_color_change, "palette")

        def on_selection_change_editor(change):
            self._scatter.selection(change["new"])
        self._editor.observe(on_selection_change_editor, ["selection"])

        def on_selection_change_tag_editor(change):
            self._scatter.selection(change["new"])
        self._tag_editor.observe(on_selection_change_tag_editor, ["selection"])


        # Sync scatter selection → both editors, and push to JS immediately
        def on_selection_change_plot(change):
            selection_indices = [int(n) for n in change["new"]]
            self._editor.selection = selection_indices
            self._tag_editor.selection = selection_indices
            # Force frontend to get updated selection now
            self._tag_editor.send_state()

            # Reset all toggles in tag widget if you double-click to clear the selection
            if not selection_indices:
                for tag in self._tag_editor.tag_set:
                    tag["include_btn_active"] = False
                    tag["exclude_btn_active"] = False
                # Force a new list reference so traitlets sync to JS
                self._tag_editor.tag_set = list(self._tag_editor.tag_set)
                self._tag_editor.calculate_selection()
                self._tag_editor.send_state()

                self._topbar.clear_search()

            # Rebuild quak dataframe widget based on selection
            # I don't think there is a way to filter programatically
            # https://github.com/manzt/quak/issues/88
            if selection_indices:
                self._quak_container.children = [quak.Widget(self._data.iloc[selection_indices])]
            else:
                self._quak_container.children = [quak.Widget(self._data.iloc[[]])]            

            # Render content if there is a callback
            self._update_content_pane(selection_indices)
                

        self._scatter.widget.observe(on_selection_change_plot, ["selection"])

        def on_change_labels(change):
            self._scatter.data(
                self._data.join(self.labels(name="__labels__")),
                how="left"
            )
        self._editor.observe(on_change_labels, "labels")

        # Top search bar handler
        def handle_search(query: str):
            if query:
                mask = pd.Series(False, index=self._data.index)
                for col in self._search_columns:
                    if col in self._data.columns:
                        mask |= self._data[col].astype(str).str.contains(query, case=False, na=False)

                indices = self._data.index[mask].tolist()
                self._scatter.selection(indices)
                self._editor.selection = indices
                self._tag_editor.selection = indices
                # Force traitlets sync to frontend immediately
                self._editor.send_state()
                self._tag_editor.send_state()
            else:
                # Empty query clears selection
                self._scatter.selection([])
                self._editor.selection = []
                self._tag_editor.selection = []
                self._editor.send_state()
                self._tag_editor.send_state()

            self._editor.send_state()
            self._tag_editor.send_state()

        self._topbar._on_search = handle_search


    def _update_content_pane(self, indices):
        """Internal method to update right pane when scatter selection changes."""
        self._content_pane.clear_output()

        with self._content_pane:
            if not indices:
                print("No points selected.")
                return
            
            selected_df = self._data.iloc[indices]

            if callable(self._content_renderer):
                # Let user completely control what is displayed
                self._content_renderer(indices, selected_df, self._content_pane)
            else:
                print(f"You've selected {len(indices)} points")
                print(f"Selected points: {indices}")

    def labels(self, name: str = "labels", colors: str = "") -> pd.Series:
        assert not colors
        labels = pd.Series(
            pd.Categorical(self._editor.labels, categories=self._editor.categories),
            index=self._data.index,
            name=name,
        ).to_frame()
        return labels

    def show(self) -> wg.Widget:
        self._scatter.height = self._height
        sw = self._scatter.show()
        sw.height = self._height
        sw.layout.flex = "6 1 auto"
        sw.layout.height = "100%"

        # Common style for left and right panes
        side_pane_style = dict(
            flex="1 0 auto",
            min_width="1in",
            max_width="2.5in",
            margin="0px 5px 0px 0px",
            height=f"{self._height + 25}px",
            overflow_y="auto"
        )
        self._editor.layout = wg.Layout(**side_pane_style)
        self._tag_editor.layout = wg.Layout(**side_pane_style)
        self._content_pane.layout = wg.Layout(**side_pane_style)

        # Create a tab widget for both LabelEditor and TagEditor
        editors_tab = wg.Tab(children=[self._editor, self._tag_editor])
        editors_tab.set_title(0, "Labels")
        editors_tab.set_title(1, "Tags")
        editors_tab.layout = wg.Layout(**side_pane_style)

        # Top search bar
        self._topbar.layout.flex = "0 0 auto"

        # Force it to not overflow if lots of content is selected
        scrollable_content = wg.Box(
            [self._content_pane],
            layout=wg.Layout(**side_pane_style
            )
        )

        hbox = wg.HBox(
            children=[editors_tab, sw, scrollable_content],
            layout=wg.Layout(
                display="flex",
                flex_flow="row wrap",
                align_items="stretch",
                align_content="stretch",
                height=f"{self._height + 25}px",
                flex="1 1 auto",
                width="100%",
            )
        )

        return wg.VBox(
            children=[self._topbar, hbox, self._quak_container],
            layout=wg.Layout(
                display="flex",
                flex_flow="column wrap",
                align_content="center",
                width="100%"
            )
        )


__all__ = [
    "CategoricalEditor",
    "Dashboard",
    "LabelEditor",
    "TagEditor",
]
