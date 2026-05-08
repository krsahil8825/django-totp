// Populate year placeholders
function populateYear() {
    const els = document.querySelectorAll("#year");
    els.forEach((el) => {
        el.textContent = new Date().getFullYear();
    });
}

// Smooth scroll for internal anchors
function enableSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute("href"));
            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });
}

// Card hover and entrance animations
function initCards() {
    const cards = document.querySelectorAll(".tool-card");
    cards.forEach((card) => {
        card.addEventListener("mouseenter", function () {
            this.style.cursor = "pointer";
        });
    });

    window.addEventListener("load", () => {
        const cards = document.querySelectorAll(".tool-card");
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.opacity = "1";
            }, index * 100);
        });
    });
}

// JSON -> SVG tool
function jsonToSvg(value) {
    let data = value;

    if (typeof data === "string") {
        const trimmed = data.trim();
        if (!trimmed) return "";

        try {
            data = JSON.parse(trimmed);
        } catch (error) {
            return trimmed
                .replace(/\\n/g, "\n")
                .replace(/\\r/g, "\r")
                .replace(/\\t/g, "\t")
                .replace(/\\"/g, '"')
                .replace(/\\\\/g, "\\")
                .replace(/svg:/g, "")
                .replace(/xmlns:svg=/g, "xmlns=");
        }
    }

    if (data && typeof data === "object") {
        if (typeof data.svg === "string") {
            return data.svg.replace(/svg:/g, "").replace(/xmlns:svg=/g, "xmlns=");
        }
        return "";
    }

    return "";
}

function render() {
    const input = document.getElementById("input");
    if (!input) return;
    const svg = jsonToSvg(input.value);
    const preview = document.getElementById("preview");
    if (preview) preview.innerHTML = svg;
}

// JSON -> TXT tool
function jsonToTxt(value, key = "backup_codes") {
    let data = value;
    if (typeof data === "string") {
        const trimmed = data.trim();
        if (!trimmed) return "";
        data = JSON.parse(trimmed);
    }
    if (!data || typeof data !== "object") return "";
    const codes = data[key];
    if (!Array.isArray(codes)) return "";
    return codes
        .map((item) => String(item).trim())
        .filter(Boolean)
        .join("\n");
}

function downloadTxt() {
    const input = document.getElementById("input");
    const filenameEl = document.getElementById("filename");
    const preview = document.getElementById("preview");
    const inputValue = input ? input.value : "";
    const fileName = filenameEl ? filenameEl.value.trim() || "output.txt" : "output.txt";
    let text = "";
    try {
        text = jsonToTxt(inputValue, "backup_codes");
    } catch (error) {
        if (preview) preview.textContent = "Invalid JSON input.";
        return;
    }
    if (!text) {
        if (preview) preview.textContent = "No backup_codes array found.";
        return;
    }
    if (preview) preview.textContent = text;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName.endsWith(".txt") ? fileName : `${fileName}.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

// Initialize common page behavior
function initHelperScripts() {
    populateYear();
    enableSmoothScroll();
    initCards();
}

// Run on DOM ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHelperScripts);
} else {
    initHelperScripts();
}

// Expose functions used by inline onclick attributes
window.render = render;
window.downloadTxt = downloadTxt;
