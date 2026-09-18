/*
 * CSRF cookie yordamchisi.
 *
 * Arena live-preview sahifa iframe ichida ochilganda brauzer "uchinchi
 * tomon" cookie bloklashini yoqishi mumkin. U holda Django serveri
 * csrftoken cookie'ni o'rnata olmaydi va foydalanuvchi "CSRF cookie
 * not set" xatosini ko'radi.
 *
 * Yechim: sahifada {% csrf_token %} hidden maydoni bo'lsa, biz shu
 * tokenni document.cookie orqali qayta o'rnatamiz — POST jonatilganda
 * cookie mavjud bo'ladi.
 */
(function () {
    if (!document.cookie) {
        // cookie butunlay o'chiq — hech narsa qila olmaymiz
        return;
    }
    function getMetaCsrf() {
        var input = document.querySelector(
            'input[name="csrfmiddlewaretoken"]'
        );
        return input ? input.value : null;
    }
    function ensureCsrfCookie() {
        var token = getMetaCsrf();
        if (!token) {
            return;
        }
        var hasCookie = document.cookie.indexOf("csrftoken=") !== -1;
        if (!hasCookie) {
            // Ayrim brauzerlar SameSite=None+Sesure uchun ham token qabul
            // qilmaydi; keng moslik uchun oddiy yozishga harakat qilamiz.
            document.cookie =
                "csrftoken=" +
                token +
                "; path=/; max-age=31449600; SameSite=None; Secure";
            document.cookie =
                "csrftoken=" +
                token +
                "; path=/; max-age=31449600";
        }
    }
    ensureCsrfCookie();

    // Formalar yuborilganda yana bir bor kafolatlaymiz
    document.addEventListener("submit", ensureCsrfCookie, true);
})();
