/* ==========================================================
   EVENTIFY CHATBOT
========================================================== */

document.addEventListener("DOMContentLoaded", function () {

    const chatbot = document.getElementById(
        "eventifyChatbot"
    );

    const toggle = document.getElementById(
        "chatbotToggle"
    );

    const closeButton = document.getElementById(
        "chatbotClose"
    );

    const windowElement = document.getElementById(
        "chatbotWindow"
    );

    const form = document.getElementById(
        "chatbotForm"
    );

    const input = document.getElementById(
        "chatbotInput"
    );

    const messages = document.getElementById(
        "chatbotMessages"
    );

    const typing = document.getElementById(
        "chatbotTyping"
    );


    /* ======================================================
       SAFETY CHECK
    ====================================================== */

    if (
        !chatbot ||
        !toggle ||
        !closeButton ||
        !windowElement ||
        !form ||
        !input ||
        !messages
    ) {

        console.error(
            "Eventify chatbot elements were not found."
        );

        return;

    }

        /* ======================================================
       QUICK QUESTIONS
    ====================================================== */

    const quickActions =
        document.querySelectorAll(
            ".chatbot-quick-action"
        );


    quickActions.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    const question =
                        button.dataset.question;


                    if (!question) {

                        return;

                    }


                    input.value =
                        question;


                    form.dispatchEvent(
                        new Event(
                            "submit",
                            {
                                bubbles: true,
                                cancelable: true
                            }
                        )
                    );

                }
            );

        }
    );

        /* ======================================================
       ENTER TO SEND
    ====================================================== */

    input.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                form.dispatchEvent(
                    new Event(
                        "submit",
                        {
                            bubbles: true,
                            cancelable: true
                        }
                    )
                );

            }

        }
    );


    /* ======================================================
       OPEN CHAT
    ====================================================== */

    toggle.addEventListener(
        "click",
        function () {

            windowElement.classList.toggle(
                "active"
            );

            toggle.setAttribute(
    "aria-expanded",
    windowElement.classList.contains("active")
);
    
          windowElement.setAttribute(
    "aria-hidden",
    !windowElement.classList.contains("active")
);


            if (
                windowElement.classList.contains(
                    "active"
                )
            ) {

                input.focus();

            }

        }
    );


    /* ======================================================
       CLOSE CHAT
    ====================================================== */

    closeButton.addEventListener(
        "click",
        function () {

            windowElement.classList.remove(
                "active"
            );

            toggle.setAttribute(
    "aria-expanded",
    "false"
);

windowElement.setAttribute(
    "aria-hidden",
    "true"
);

        }
    );


    /* ======================================================
       CLOSE WITH ESC
    ====================================================== */

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape"
            ) {

                windowElement.classList.remove(
                    "active"
                );

                toggle.setAttribute(
    "aria-expanded",
    "false"
);

windowElement.setAttribute(
    "aria-hidden",
    "true"
);

            }

        }
    );


    /* ======================================================
       CSRF TOKEN
    ====================================================== */

    function getCookie(name) {

        const cookies =
            document.cookie.split(";");


        for (
            let cookie of cookies
        ) {

            cookie = cookie.trim();


            if (
                cookie.startsWith(
                    name + "="
                )
            ) {

                return decodeURIComponent(
                    cookie.substring(
                        name.length + 1
                    )
                );

            }

        }


        return null;

    }


    /* ======================================================
   CHATBOT RESPONSE FORMATTER
====================================================== */

function renderChatbotText(
    element,
    text
) {

    if (!text) {

        return;

    }

    const lines =
        String(text).split("\n");

    lines.forEach(
        function (line, index) {

            const trimmed =
                line.trim();

            if (!trimmed) {

                if (
                    index <
                    lines.length - 1
                ) {

                    element.appendChild(
                        document.createElement("br")
                    );

                }

                return;

            }

            /* ==========================================
               BULLET POINT
            ========================================== */

            if (
                trimmed.startsWith("- ") ||
                trimmed.startsWith("* ")
            ) {

                const bullet =
                    document.createElement("div");

                bullet.className =
                    "chatbot-response-bullet";

                const icon =
                    document.createElement("span");

                icon.className =
                    "chatbot-bullet-icon";

                icon.textContent =
                    "•";

                const content =
                    document.createElement("span");

                renderInlineFormatting(
                    content,
                    trimmed.substring(2)
                );

                bullet.appendChild(icon);

                bullet.appendChild(content);

                element.appendChild(bullet);

                return;

            }

            /* ==========================================
               NUMBERED LIST
            ========================================== */

            const numbered =
                trimmed.match(
                    /^(\d+)[.)]\s+(.*)$/
                );

            if (numbered) {

                const item =
                    document.createElement("div");

                item.className =
                    "chatbot-response-number";

                const number =
                    document.createElement("span");

                number.className =
                    "chatbot-number";

                number.textContent =
                    numbered[1];

                const content =
                    document.createElement("span");

                renderInlineFormatting(
                    content,
                    numbered[2]
                );

                item.appendChild(number);

                item.appendChild(content);

                element.appendChild(item);

                return;

            }

            /* ==========================================
               NORMAL PARAGRAPH
            ========================================== */

            const paragraph =
                document.createElement("div");

            paragraph.className =
                "chatbot-response-paragraph";

            renderInlineFormatting(
                paragraph,
                trimmed
            );

            element.appendChild(
                paragraph
            );

        }
    );

}


/* ======================================================
   INLINE FORMATTING
====================================================== */

function renderInlineFormatting(
    element,
    text
) {

    const parts =
        String(text).split(
            /(\*\*[^*]+\*\*|`[^`]+`)/
        );

    parts.forEach(
        function (part) {

            if (
                part.startsWith("**") &&
                part.endsWith("**")
            ) {

                const strong =
                    document.createElement("strong");

                strong.textContent =
                    part.slice(2, -2);

                element.appendChild(
                    strong
                );

                return;

            }

            if (
                part.startsWith("`") &&
                part.endsWith("`")
            ) {

                const code =
                    document.createElement("code");

                code.textContent =
                    part.slice(1, -1);

                element.appendChild(
                    code
                );

                return;

            }

            element.appendChild(
                document.createTextNode(part)
            );

        }
    );

}


    /* ======================================================
       ADD MESSAGE
    ====================================================== */

    function addMessage(
        text,
        sender,
        links = [],
        image = null
    ) {

        const wrapper =
            document.createElement(
                "div"
            );


        wrapper.className =
            `chatbot-message ${sender}`;


        const content =
            document.createElement(
                "div"
            );


        content.className =
            "chatbot-bubble";


        const textElement =
    document.createElement(
        "div"
    );

textElement.className =
    "chatbot-message-text";

renderChatbotText(
    textElement,
    text
);


        content.appendChild(
            textElement
        );


        /* ==================================================
           INLINE IMAGE (e.g. QR ticket)
        ================================================== */

        if (image) {

            const img =
                document.createElement(
                    "img"
                );

            img.src = image;

            img.alt = "QR";

            img.className =
                "chatbot-image";

            img.style.cssText =
                "display:block;width:180px;height:180px;" +
                "margin:8px 0;border-radius:12px;" +
                "background:#fff;padding:6px;" +
                "border:1px solid #e2e8f0;";

            content.appendChild(
                img
            );

        }


        /* ==================================================
           NAVIGATION / ACTION LINKS
        ================================================== */

        if (
            Array.isArray(links) &&
            links.length > 0
        ) {

            const linksContainer =
                document.createElement(
                    "div"
                );


            linksContainer.className =
                "chatbot-links";


            links.forEach(
                function (link) {

                    if (
                        !link.label ||
                        !link.url
                    ) {

                        return;

                    }


                    const anchor =
                        document.createElement(
                            "a"
                        );


                    anchor.href =
                        link.url;


                    anchor.className =
                        "chatbot-link";


                    anchor.textContent =
                        link.label;


                    /* ========================================
                       CONFIRM CANCELLATION
                    ======================================== */

                    if (
                        link.action ===
                        "confirm_cancel"
                    ) {

                        anchor.href = "#";


                        anchor.addEventListener(
                            "click",
                            function (event) {

                                event.preventDefault();

                                event.stopPropagation();


                                confirmCancellation(
                                    link.registration_id,
                                    link.event_title
                                );

                            }
                        );

                    }


                    /* ========================================
                       CANCEL CONFIRMATION
                    ======================================== */

                    else if (
                        link.action ===
                        "cancel_confirmation"
                    ) {

                        anchor.href = "#";


                        anchor.addEventListener(
                            "click",
                            function (event) {

                                event.preventDefault();

                                event.stopPropagation();


                                addMessage(
                                    "Okay, I’ll keep your registration. 👍",
                                    "bot"
                                );

                            }
                        );

                    }


                    /* ========================================
                       NORMAL NAVIGATION LINK
                    ======================================== */

                    else {

                        anchor.target =
                            "_self";

                    }


                    /* ========================================
                       LINK ICON
                    ======================================== */

                    const icon =
                        document.createElement(
                            "i"
                        );


                    icon.className =
                        "bi bi-arrow-right";


                    anchor.appendChild(
                        icon
                    );


                    linksContainer.appendChild(
                        anchor
                    );

                }
            );


            content.appendChild(
                linksContainer
            );

        }


        wrapper.appendChild(
            content
        );


        messages.appendChild(
            wrapper
        );


        messages.scrollTop =
            messages.scrollHeight;

    }


    /* ======================================================
       TYPING INDICATOR
    ====================================================== */

    function showTyping() {

        if (!typing) {

            return;

        }


        typing.classList.add(
            "active"
        );


        messages.scrollTop =
            messages.scrollHeight;

    }


    function hideTyping() {

        if (!typing) {

            return;

        }


        typing.classList.remove(
            "active"
        );

    }


    /* ======================================================
       CONFIRM CANCELLATION
       
       IMPORTANT:
       This function is INSIDE DOMContentLoaded so it can
       access addMessage().
    ====================================================== */

    async function confirmCancellation(
        registrationId,
        eventTitle
    ) {

        console.log(
            "Cancellation clicked:",
            registrationId,
            eventTitle
        );


        addMessage(
            `Cancelling your ${eventTitle} registration...`,
            "bot"
        );


        try {

            const response =
                await fetch(
                    `/my-registrations/${registrationId}/cancel/`,
                    {
                        method: "GET",

                        credentials:
                            "same-origin",

                        headers: {
                            "X-Requested-With":
                                "XMLHttpRequest"
                        }
                    }
                );


            console.log(
                "Cancellation response:",
                response.status,
                response.url
            );


            /* ==============================================
               SUCCESS
            ============================================== */

            if (
                response.ok ||
                response.redirected
            ) {

                addMessage(
                    `Your registration for ${eventTitle} `
                    + `has been cancelled successfully. ✅`,
                    "bot"
                );


                addMessage(
                    "Your registration list has been updated.",
                    "bot",
                    [
                        {
                            label:
                                "My Registrations",

                            url:
                                "/my-registrations/"
                        }
                    ]
                );


                return;

            }


            /* ==============================================
               SERVER ERROR
            ============================================== */

            addMessage(
                "I couldn't cancel the registration. Please try again.",
                "bot"
            );

        }

        catch (error) {

            console.error(
                "Cancellation error:",
                error
            );


            addMessage(
                "Something went wrong while cancelling your registration.",
                "bot"
            );

        }

    }


    /* ======================================================
       SEND MESSAGE
    ====================================================== */

    form.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();


            const message =
                input.value.trim();


            if (!message) {

                return;

            }


            /* ----------------------------------------------
               USER MESSAGE
            ---------------------------------------------- */

            addMessage(
                message,
                "user"
            );


            input.value = "";

            input.disabled = true;


            const sendButton =
                form.querySelector(
                    "button"
                );


            if (sendButton) {

                sendButton.disabled =
                    true;

            }


            showTyping();


            try {

                const csrfToken =
                    getCookie(
                        "csrftoken"
                    );


                const formData =
                    new URLSearchParams();


                formData.append(
                    "message",
                    message
                );


                const response =
                    await fetch(
                        "/chatbot/api/chat/",
                        {

                            method: "POST",

                            headers: {

                                "Content-Type":
                                    "application/x-www-form-urlencoded",

                                "X-CSRFToken":
                                    csrfToken,

                            },

                            body:
                                formData.toString(),

                        }
                    );


                const data =
                    await response.json();


                hideTyping();


                /* ==================================================
   HANDLE RESPONSE
================================================== */

if (response.status === 429) {

    addMessage(
        data.reply ||
        "The AI assistant is temporarily unavailable because the AI service has reached its usage limit. Please try again later. ⏳",
        "bot",
        [],
        data.image || null
    );

}
else if (data.reply) {

    addMessage(
        data.reply,
        "bot",
        data.links || [],
        data.image || null
    );

}
else {

    addMessage(
        "Sorry, I couldn't process that request. Please try again.",
        "bot"
    );

}

                

            }

            catch (error) {

                console.error(
                    "Chatbot error:",
                    error
                );


                hideTyping();


                addMessage(
                    "I couldn't connect to the Eventify server. Please try again.",
                    "bot"
                );

            }


            input.disabled = false;


            if (sendButton) {

                sendButton.disabled =
                    false;

            }


            input.focus();

        }
    );

});