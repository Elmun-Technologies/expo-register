/* ==========================================================
   EVENTIFY - BACK TO TOP BUTTON
   Self-contained: only runs if #backToTop exists on the page.
   ========================================================== */

document.addEventListener("DOMContentLoaded", function () {

    const topBtn = document.getElementById("backToTop");

    if (!topBtn) {
        return;
    }

    window.addEventListener("scroll", function () {

        if (window.scrollY > 300) {
            topBtn.classList.add("show");
        } else {
            topBtn.classList.remove("show");
        }

    });

    topBtn.addEventListener("click", function () {

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    });

});
