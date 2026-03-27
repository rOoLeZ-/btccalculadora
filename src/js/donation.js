function renderDonationQr() {
  const qrNode = document.getElementById("bolt12-qr");
  if (!qrNode) return;

  const qrText = qrNode.dataset.qrText || "";
  if (!qrText) {
    qrNode.textContent = "No hemos podido cargar el QR.";
    return;
  }

  if (typeof QRCode === "undefined") {
    qrNode.textContent = "No hemos podido cargar el QR.";
    return;
  }

  qrNode.innerHTML = "";
  new QRCode(qrNode, {
    text: qrText,
    width: 220,
    height: 220,
    colorDark: "#111315",
    colorLight: "#f6f7f9",
    correctLevel: QRCode.CorrectLevel.L
  });
}

async function copyDonationText(text) {
  if (!text) return false;

  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "absolute";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();

    let copied = false;
    try {
      copied = document.execCommand("copy");
    } finally {
      document.body.removeChild(textarea);
    }

    return copied;
  }
}

function initDonationCopyButtons() {
  document.querySelectorAll(".donation-copy-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const targetId = button.dataset.copyTarget;
      const directValue = button.dataset.copyValue;
      const target = targetId ? document.getElementById(targetId) : null;
      const text = directValue || target?.textContent?.trim() || "";
      if (!text) return;

      const copied = await copyDonationText(text);
      if (!copied) return;

      const originalLabel = button.dataset.originalLabel || button.textContent;
      button.dataset.originalLabel = originalLabel;
      button.textContent = "Copiado";
      button.classList.add("is-copied");

      window.setTimeout(() => {
        button.textContent = originalLabel;
        button.classList.remove("is-copied");
      }, 1800);
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderDonationQr();
  initDonationCopyButtons();
});
