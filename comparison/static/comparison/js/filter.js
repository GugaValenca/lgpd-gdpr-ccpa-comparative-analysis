/**
 * Instant client-side category filtering for the comparison grid.
 * Search (the "q" param) is handled server-side in views.py so the page
 * works without JavaScript; this just layers snappier category filtering
 * on top of whatever the server already rendered.
 */
(function () {
    "use strict";

    const filterBar = document.getElementById("category-filter");
    const grid = document.getElementById("comparison-grid");
    if (!filterBar || !grid) return;

    const chips = filterBar.querySelectorAll(".chip");
    const cards = grid.querySelectorAll(".category-card");

    filterBar.addEventListener("click", function (event) {
        const chip = event.target.closest(".chip");
        if (!chip) return;

        chips.forEach((c) => c.classList.remove("is-active"));
        chip.classList.add("is-active");

        const filter = chip.dataset.filter;
        cards.forEach((card) => {
            const match = filter === "all" || card.dataset.category === filter;
            card.hidden = !match;
        });
    });
})();
