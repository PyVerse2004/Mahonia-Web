/**
 * Mahonia Luxury Toast Notification Controller
 * Handles 2-second timed auto-dismissal, pause on hover, smooth entrance/exit animations,
 * and dynamic client-side toast triggers.
 */
(function () {
    "use strict";

    function initToast(toast) {
        if (!toast || toast._toastInitialized) return;
        toast._toastInitialized = true;

        const duration = parseInt(toast.dataset.duration || 2000, 10);
        let remaining = duration;
        let startTime = Date.now();
        let timerId = null;
        let isDismissing = false;

        const progressBar = toast.querySelector(".mahonia-toast-timer-progress");
        if (progressBar) {
            progressBar.style.animationDuration = duration + "ms";
        }

        function dismiss() {
            if (isDismissing) return;
            isDismissing = true;
            if (timerId) {
                clearTimeout(timerId);
                timerId = null;
            }

            toast.classList.add("toast-hiding");

            function onEnd() {
                if (toast.parentElement) {
                    toast.parentElement.removeChild(toast);
                }
            }

            toast.addEventListener("animationend", onEnd, { once: true });
            // Fallback in case animationend does not fire
            setTimeout(onEnd, 400);
        }

        function startTimer() {
            startTime = Date.now();
            timerId = setTimeout(dismiss, remaining);
            if (progressBar) {
                progressBar.style.animationPlayState = "running";
            }
        }

        function pauseTimer() {
            if (timerId) {
                clearTimeout(timerId);
                timerId = null;
                const elapsed = Date.now() - startTime;
                remaining = Math.max(0, remaining - elapsed);
                if (progressBar) {
                    progressBar.style.animationPlayState = "paused";
                }
            }
        }

        // Hover interactions: pause on enter, resume on leave
        toast.addEventListener("mouseenter", pauseTimer);
        toast.addEventListener("mouseleave", function () {
            if (remaining > 0) {
                startTimer();
            } else {
                dismiss();
            }
        });

        // Close button click
        const closeBtn = toast.querySelector(".mahonia-toast-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", function (e) {
                e.preventDefault();
                dismiss();
            });
        }

        // Start countdown
        startTimer();
    }

    function initExistingToasts() {
        const toasts = document.querySelectorAll(".mahonia-toast");
        toasts.forEach(initToast);
    }

    // Expose global showMahoniaToast helper for dynamic client-side notifications
    window.showMahoniaToast = function (message, type, duration) {
        type = type || "success";
        duration = duration !== undefined ? duration : 2000;

        let container = document.getElementById("mahoniaToastContainer");
        if (!container) {
            container = document.createElement("div");
            container.id = "mahoniaToastContainer";
            container.className = "mahonia-toast-container";
            container.setAttribute("aria-live", "polite");
            container.setAttribute("aria-atomic", "true");
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = "mahonia-toast mahonia-toast-" + type;
        toast.setAttribute("role", "alert");
        toast.dataset.duration = duration;

        let iconClass = "bi-check-circle-fill";
        let badgeText = "موفقیت‌آمیز";
        if (type === "error" || type === "danger") {
            iconClass = "bi-exclamation-octagon-fill";
            badgeText = "خطا در عملیات";
        } else if (type === "warning") {
            iconClass = "bi-exclamation-triangle-fill";
            badgeText = "توجه";
        } else if (type === "info") {
            iconClass = "bi-info-circle-fill";
            badgeText = "پیام سامانه";
        }

        const secondsText = (duration / 1000).toFixed(0) + " ثانیه";

        toast.innerHTML = `
            <div class="mahonia-toast-icon-wrapper">
                <i class="bi ${iconClass}"></i>
            </div>
            <div class="mahonia-toast-content">
                <div class="mahonia-toast-header">
                    <span class="mahonia-toast-badge">${badgeText}</span>
                    <span class="mahonia-toast-time"><i class="bi bi-clock-history"></i> ${secondsText}</span>
                </div>
                <div class="mahonia-toast-message">${message}</div>
            </div>
            <button type="button" class="mahonia-toast-close" aria-label="بستن">
                <i class="bi bi-x-lg"></i>
            </button>
            <div class="mahonia-toast-timer-bar">
                <div class="mahonia-toast-timer-progress"></div>
            </div>
        `;

        container.appendChild(toast);
        initToast(toast);
        return toast;
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initExistingToasts);
    } else {
        initExistingToasts();
    }
})();
