/**
 * Mahonia Live Filter & Real-Time Instant Search
 * Debounced live search and filtering without page reload across all catalog, sales, persons, reports, and inventory lists.
 */
(function () {
    "use strict";

    let activeFilterRequests = 0;
    let loaderStartTime = 0;
    let hideTimer = null;

    function getOrCreateGlobalLoader() {
        let loader = document.getElementById("liveFilterGlobalLoader");
        if (!loader) {
            loader = document.createElement("div");
            loader.id = "liveFilterGlobalLoader";
            loader.className = "live-filter-global-overlay";
            loader.setAttribute("aria-hidden", "true");
            loader.setAttribute("role", "status");
            loader.setAttribute("aria-live", "polite");
            loader.innerHTML = `
                <div class="live-filter-center-card">
                    <div class="live-filter-orb-wrapper">
                        <div class="live-filter-spinner-outer"></div>
                        <div class="live-filter-spinner-inner"></div>
                        <div class="live-filter-orb-glow"></div>
                        <div class="live-filter-orb-core">
                            <i class="bi bi-arrow-repeat live-filter-core-icon"></i>
                        </div>
                    </div>
                    <div class="live-filter-text-group">
                        <div class="live-filter-title text-gradient-gold">در حال به‌روزرسانی اطلاعات...</div>
                        <div class="live-filter-subtitle">جستجو و فیلتر لحظه‌ای ماهونیا</div>
                    </div>
                    <div class="live-filter-dots">
                        <span class="live-filter-dot dot-1"></span>
                        <span class="live-filter-dot dot-2"></span>
                        <span class="live-filter-dot dot-3"></span>
                    </div>
                </div>
            `;
            document.body.appendChild(loader);
        }
        return loader;
    }

    function showCenterLoader() {
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        activeFilterRequests++;
        const loader = getOrCreateGlobalLoader();
        loaderStartTime = Date.now();
        loader.classList.add("is-active");
        loader.setAttribute("aria-hidden", "false");
        document.body.classList.add("is-live-filtering");
    }

    function hideCenterLoader() {
        activeFilterRequests = Math.max(0, activeFilterRequests - 1);
        if (activeFilterRequests > 0) {
            return;
        }

        const loader = getOrCreateGlobalLoader();
        const elapsed = Date.now() - loaderStartTime;
        const delay = Math.max(0, 220 - elapsed);

        hideTimer = setTimeout(() => {
            if (activeFilterRequests === 0) {
                loader.classList.remove("is-active");
                loader.setAttribute("aria-hidden", "true");
                document.body.classList.remove("is-live-filtering");
            }
            hideTimer = null;
        }, delay);
    }

    function debounce(fn, delay) {
        let timer = null;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function initLiveFilter() {
        const forms = document.querySelectorAll("form.live-filter-form, form[data-live-filter='true'], .filter-card form");
        if (!forms.length) return;

        forms.forEach(function (form) {
            if (form._liveFilterInitialized) return;
            form._liveFilterInitialized = true;

            const targetSelector = form.dataset.resultsTarget || "#liveResultsContainer";
            const resultsContainer = document.querySelector(targetSelector);
            if (!resultsContainer) return;

            let currentController = null;

            // Ensure a live loading shimmer bar exists inside results container
            if (!resultsContainer.querySelector(".live-filter-loading-bar")) {
                const bar = document.createElement("div");
                bar.className = "live-filter-loading-bar";
                resultsContainer.insertBefore(bar, resultsContainer.firstChild);
            }

            // Decorate search inputs with subtle spinner wrapper
            const searchInputs = form.querySelectorAll("input[type='search'], input[name='q']");
            searchInputs.forEach(input => {
                const parent = input.parentElement;
                if (parent && !parent.querySelector(".live-search-spinner")) {
                    parent.classList.add("live-search-input-wrapper");
                    const spinner = document.createElement("span");
                    spinner.className = "live-search-spinner";
                    parent.appendChild(spinner);
                }
            });

            function buildUrl(overrideUrl) {
                if (overrideUrl) return overrideUrl;
                const formData = new FormData(form);
                const params = new URLSearchParams();
                for (const [key, val] of formData.entries()) {
                    const trimmed = typeof val === "string" ? val.trim() : val;
                    if (trimmed !== "" && trimmed !== null && trimmed !== undefined) {
                        params.append(key, trimmed);
                    }
                }
                const base = form.getAttribute("action") || window.location.pathname;
                const qs = params.toString();
                return qs ? `${base}?${qs}` : base;
            }

            function executeFilter(overrideUrl) {
                const url = buildUrl(overrideUrl);

                if (currentController) {
                    currentController.abort();
                }
                currentController = new AbortController();

                showCenterLoader();
                resultsContainer.classList.add("is-loading");
                form.classList.add("is-searching");

                fetch(url, {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    signal: currentController.signal
                })
                .then(response => {
                    if (!response.ok) throw new Error("HTTP error " + response.status);
                    return response.text();
                })
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, "text/html");

                    // 1. Update main results container (table / grid + pagination)
                    const newResults = doc.querySelector(targetSelector);
                    if (newResults) {
                        resultsContainer.innerHTML = newResults.innerHTML;
                        if (!resultsContainer.querySelector(".live-filter-loading-bar")) {
                            const bar = document.createElement("div");
                            bar.className = "live-filter-loading-bar";
                            resultsContainer.insertBefore(bar, resultsContainer.firstChild);
                        }
                    }

                    // 2. Update optional summary cards (profit/loss report)
                    const currentSummary = document.getElementById("reportSummaryCards");
                    const newSummary = doc.getElementById("reportSummaryCards");
                    if (currentSummary && newSummary) {
                        currentSummary.innerHTML = newSummary.innerHTML;
                    }

                    // 3. Update optional subtitle (profit/loss report date range)
                    const currentSubtitle = document.getElementById("reportSubtitle");
                    const newSubtitle = doc.getElementById("reportSubtitle");
                    if (currentSubtitle && newSubtitle) {
                        currentSubtitle.innerHTML = newSubtitle.innerHTML;
                    }

                    // 4. Update browser URL without full reload
                    window.history.replaceState(null, "", url);

                    // Re-bind pagination and pill remove clicks in freshly loaded HTML
                    bindPagination();
                })
                .catch(err => {
                    if (err.name !== "AbortError") {
                        console.error("Live filter error:", err);
                    }
                })
                .finally(() => {
                    resultsContainer.classList.remove("is-loading");
                    form.classList.remove("is-searching");
                    hideCenterLoader();
                });
            }

            const debouncedFilter = debounce(() => executeFilter(), 320);

            // 1. Live text & search & price inputs typing
            form.querySelectorAll("input[type='text'], input[type='search'], input[type='number'], input[name='q'], input[name='min_price'], input[name='max_price']").forEach(input => {
                input.addEventListener("input", function () {
                    debouncedFilter();
                });
                input.addEventListener("keydown", function (e) {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        executeFilter();
                    }
                });
            });

            // 2. Select dropdowns and date inputs
            form.querySelectorAll("select, input[type='date'], input.jalali-date-input, input[name='date']").forEach(elem => {
                elem.addEventListener("change", function () {
                    executeFilter();
                });
            });

            // 3. Clear button / link click
            form.querySelectorAll("a, button, .btn-clear-filter").forEach(btn => {
                const text = btn.textContent.trim();
                if (text.includes("پاک") || btn.classList.contains("btn-clear-filter")) {
                    btn.addEventListener("click", function (e) {
                        e.preventDefault();
                        form.reset();
                        form.querySelectorAll("input").forEach(i => {
                            if (i.type !== "hidden") i.value = "";
                        });
                        form.querySelectorAll("select").forEach(s => s.selectedIndex = 0);
                        executeFilter(form.getAttribute("action") || window.location.pathname);
                    });
                }
            });

            // 4. Form submit button (manual click fallback)
            form.addEventListener("submit", function (e) {
                e.preventDefault();
                executeFilter();
            });

            // 5. Intercept pagination & filter pill links inside results container
            function bindPagination() {
                resultsContainer.querySelectorAll(".mahonia-pagination a, nav[aria-label='صفحه‌بندی'] a").forEach(link => {
                    link.addEventListener("click", function (e) {
                        e.preventDefault();
                        const href = this.getAttribute("href");
                        if (href && href !== "#") {
                            executeFilter(href);
                            resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
                        }
                    });
                });

                resultsContainer.querySelectorAll(".filter-pill-remove, .active-filters-bar a").forEach(link => {
                    link.addEventListener("click", function (e) {
                        e.preventDefault();
                        const href = this.getAttribute("href");
                        if (href) {
                            try {
                                const targetUrl = new URL(href, window.location.origin);
                                form.querySelectorAll("input[name]").forEach(input => {
                                    if (input.type !== "hidden") {
                                        input.value = targetUrl.searchParams.get(input.name) || "";
                                    }
                                });
                            } catch (err) {}
                            executeFilter(href);
                        }
                    });
                });
            }

            bindPagination();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLiveFilter);
    } else {
        initLiveFilter();
    }
})();

