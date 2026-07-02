export default {
    initialize({model}) { },
    
    render({model, el}) {
        el.classList.add("tnt-topbar")

        const reset = document.createElement("button")
        reset.title = "Reset plot display"
        reset.innerHTML = "Reset"
        el.appendChild(reset)

        const search = document.createElement("input")
        search.type = "text"
        search.placeholder = "Search"
        search.classList.add("topbar-search")

        // Don't search on every keystroke, wait until the user has stopped typing
        let searchTimeout = null;
        const wait_time_milliseconds = 250;

        function sendSearch(query) {
            model.send({
                action: "search",
                query
            });
        }
        search.addEventListener("input", (ev) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                sendSearch(ev.target.value);
            }, wait_time_milliseconds);
        });

        reset.addEventListener("click", () => {
            search.value = "";
            sendSearch("");
        });

        el.appendChild(search)

        // Clear search term if selection is reset
        model.on("msg:custom", (content) => {
            if (content.action === "clear_search") {
                search.value = "";
            }
        });
        
    },
}
