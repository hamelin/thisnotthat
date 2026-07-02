function render({ model, el }) {
  let filterText = "";

function updateTagState(tag_id, newState) {
    const tagSet = model.get("tag_set") || [];
    const updatedTags = tagSet.map(t => {
        if (t.tag_id === tag_id) {
            return {
                ...t,
                include_btn_active: newState === "right",
                exclude_btn_active: newState === "left"
            };
        }
        return t;
    });
    model.set("tag_set", [...updatedTags]); // new array reference
    model.save_changes();
}

  function buildUI(tagSet) {
    const includedTags = tagSet.filter(t => t.include_btn_active);
    const excludedTags = tagSet.filter(t => t.exclude_btn_active);

    el.innerHTML = `
      <div class="tag-editor-container">
        <div class="active-tag-area">
          <div class="active-tags included">
            <strong>Included:</strong>
            ${includedTags.length
              ? includedTags.map(t =>
                  `<span class="quick-remove included-tag" data-id="${t.tag_id}">${t.tag}</span>`
                ).join(", ")
              : "<em>None</em>"}
          </div>
          <div class="active-tags excluded">
            <strong>Excluded:</strong>
            ${excludedTags.length
              ? excludedTags.map(t =>
                  `<span class="quick-remove excluded-tag" data-id="${t.tag_id}">${t.tag}</span>`
                ).join(", ")
              : "<em>None</em>"}
          </div>
        </div>

        <div class="search-container">
          <input type="text" id="tag-search" placeholder="Search tags..." />
        </div>

        <div class="button-grid"></div>

        <div class="add-tag-container">
          <input type="text" id="new-tag-input" placeholder="New tag..." />
          <button id="add-tag-btn">Add</button>
        </div>
      </div>
    `;

    const searchBox = el.querySelector("#tag-search");
    searchBox.value = filterText;
    searchBox.addEventListener("input", (e) => {
      filterText = e.target.value;
      renderFilteredGrid(model.get("tag_set"));
    });

    const quickRemove = (tag_id) => {
      updateTagState(tag_id, "center");
    };
    el.querySelectorAll(".quick-remove.included-tag").forEach(span => {
      span.onclick = () => quickRemove(parseInt(span.dataset.id, 10));
    });
    el.querySelectorAll(".quick-remove.excluded-tag").forEach(span => {
      span.onclick = () => quickRemove(parseInt(span.dataset.id, 10));
    });

    renderFilteredGrid(tagSet);

    const newTagInput = el.querySelector("#new-tag-input");
    const addTagBtn = el.querySelector("#add-tag-btn");

    function addTagToSelection(tagName) {
        const selection = model.get("selection") || [];

        if (!tagName.trim()) return;

        // Let python create the tag and assign IDs
        model.send({
            action: "assign_tag_to_selection",
            tag: tagName,
            assign: selection.length > 0,
            assign_indices: selection,
            auto_include: true
        });
    }

    addTagBtn.addEventListener("click", () => {
        addTagToSelection(newTagInput.value);
        // Force immediate fetch from model and refresh UI highlight
        setTimeout(() => {
            const selection = model.get("selection");
            if (selection && selection.length) {
                // Force scatter selection highlight
                model.set("selection", [...selection]);
                model.save_changes();
            }
        }, 50);
    });

  
    newTagInput.addEventListener("keypress", e => {
      if (e.key === "Enter") addTagToSelection(newTagInput.value);
    });
  }

  function renderFilteredGrid(tagSet, scrollToId = null) {
    const gridEl = el.querySelector(".button-grid");

    const sortedTags = [...tagSet].sort((a, b) =>
      a.tag.toLowerCase().localeCompare(b.tag.toLowerCase())
    );
    const filteredTags = sortedTags.filter(tag =>
      tag.tag.toLowerCase().includes(filterText.toLowerCase())
    );

    gridEl.innerHTML = "";
    filteredTags.forEach(tag => {
      const itemEl = document.createElement("div");
      itemEl.className = "button-item";
      itemEl.dataset.tagId = tag.tag_id;

      const switchContainer = document.createElement("div");
      switchContainer.className = "triple-switch";
      switchContainer.innerHTML = `<span>✕</span><span>✓</span>`;

      const knob = document.createElement("div");
      knob.className = "knob";
      switchContainer.appendChild(knob);

      const states = ["left", "center", "right"];
      const positions = { "left": 3, "center": 20, "right": 37 };
      let currentState = tag.exclude_btn_active ? "left"
                        : tag.include_btn_active ? "right"
                        : "center";

      function updateUI(state) {
        switchContainer.classList.remove("left", "center", "right");
        switchContainer.classList.add(state);
        knob.style.left = positions[state] + "px";
      }
      updateUI(currentState);

      switchContainer.addEventListener("click", (evt) => {
        const rect = switchContainer.getBoundingClientRect();
        const x = evt.clientX - rect.left;
        const third = rect.width / 3;
        if (x < third) currentState = "left";
        else if (x < 2 * third) currentState = "center";
        else currentState = "right";
        updateUI(currentState);
        updateTagState(tag.tag_id, currentState);
      });

      const label = document.createElement("span");
      label.textContent = tag.tag;
      label.className = "tag-label";

      const editIcon = document.createElement("img");
      editIcon.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMCAyMCI+PHBhdGggZD0iTTE0LjY5IDIuODZsMi40NSAyLjQ1LTkuMTkgOS4xOUg1LjV2LTIuNDVsOS4xOS05LjE5ek0xOC4xIDEuNDVhMS41IDEuNSAwIDAgMC0yLjEyIDBsLTEuMDYgMS4wNiAyLjQ1IDIuNDUgMS4wNi0xLjA2YTEuNSAxLjUgMCAwIDAgMC0yLjEyTDE4LjEgMS40NXoiIGZpbGw9ImN1cnJlbnRDb2xvciIvPjwvc3ZnPg==";
      editIcon.className = "edit-icon";
      editIcon.title = "Edit tag";

      const addIcon = document.createElement("img");
      addIcon.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDE0IDE0Ij48cmVjdCB4PSI2IiB5PSIyLjUiIHdpZHRoPSIyIiBoZWlnaHQ9IjkiIGZpbGw9ImN1cnJlbnRDb2xvciIvPjxyZWN0IHg9IjIuNSIgeT0iNiIgd2lkdGg9IjkiIGhlaWdodD0iMiIgZmlsbD0iY3VycmVudENvbG9yIi8+PC9zdmc+";
      addIcon.className = "add-icon";
      addIcon.title = "Add tag to selected points";

      const removeIcon = document.createElement("img");
      removeIcon.src = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDE0IDE0Ij48cmVjdCB4PSI2IiB5PSIyIiB3aWR0aD0iMiIgaGVpZ2h0PSIxMCIgZmlsbD0iY3VycmVudENvbG9yIiB0cmFuc2Zvcm09InJvdGF0ZSg0NSA3IDcpIi8+PHJlY3QgeD0iNiIgeT0iMiIgd2lkdGg9IjIiIGhlaWdodD0iMTAiIGZpbGw9ImN1cnJlbnRDb2xvciIgdHJhbnNmb3JtPSJyb3RhdGUoLTQ1IDcgNykiLz48L3N2Zz4=";
      removeIcon.className = "remove-icon";
      removeIcon.title = "Remove tag from selected points";

      // Inline edit
      editIcon.addEventListener("click", () => {
        const input = document.createElement("input");
        input.type = "text";
        input.value = tag.tag;
        input.className = "edit-input";

        const finishEdit = () => {
          const newName = input.value.trim();
          if (!newName) {
            buildUI(model.get("tag_set"));
            return;
          }
          const tagSetCurrent = model.get("tag_set") || [];
          const updatedTags = tagSetCurrent.map(t =>
            t.tag_id === tag.tag_id ? { ...t, tag: newName } : t
          );
          model.set("tag_set", updatedTags);
          model.save_changes();
          buildUI(model.get("tag_set"));
        };

        input.addEventListener("blur", finishEdit);
        input.addEventListener("keypress", e => { if (e.key === "Enter") finishEdit(); });
        label.replaceWith(input);
        input.focus();
      });

      addIcon.addEventListener("click", () => {
        const selection = model.get("selection") || [];
        console.log(selection);
        if (!selection.length) {
          alert("No points selected.");
          return;
        }
        model.send({
          action: "assign_tag_to_selection",
          tag_id: tag.tag_id,
          tag: tag.tag,
          assign: true,
          assign_indices: selection,
          auto_include: true
        });
        addIcon.classList.add("clicked");
        setTimeout(() => addIcon.classList.remove("clicked"), 400);
      });

      removeIcon.addEventListener("click", () => {
        const selection = model.get("selection") || [];
        if (!selection.length) {
          alert("No points selected.");
          return;
        }
        model.send({
          action: "remove_tag_from_selection",
          tag_id: tag.tag_id,
          tag: tag.tag,
          auto_include: true
        });
        removeIcon.classList.add("clicked");
        setTimeout(() => removeIcon.classList.remove("clicked"), 400);
      });

      const iconGroup = document.createElement("span");
      iconGroup.className = "icon-group";
      iconGroup.appendChild(editIcon);
      iconGroup.appendChild(addIcon);
      iconGroup.appendChild(removeIcon);

      itemEl.appendChild(switchContainer);
      itemEl.appendChild(label);
      itemEl.appendChild(iconGroup);
      gridEl.appendChild(itemEl);
    });
  }

  buildUI(model.get("tag_set"));

  model.on("change:tag_set", () => buildUI(model.get("tag_set")));
  // model.on("change:selection", () => console.log("Selection changed:", model.get("selection")));
  model.on('msg:custom', (content) => {
    if (content.debug) {
      console.log("PY DEBUG:", content.debug);
    }
  });

}

export default { render };
