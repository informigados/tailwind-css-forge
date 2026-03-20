(function () {
  const phaseElement = document.getElementById("boot-phase");
  const detailElement = document.getElementById("boot-detail");
  const errorElement = document.getElementById("boot-error");

  const handleStatus = (event) => {
    const detail = event.detail ?? {};
    if (phaseElement && typeof detail.phase === "string") {
      phaseElement.textContent = detail.phase;
    }

    if (detailElement && typeof detail.detail === "string") {
      detailElement.textContent = detail.detail;
    }

    if (!errorElement) {
      return;
    }

    if (typeof detail.error === "string" && detail.error.length > 0) {
      errorElement.hidden = false;
      errorElement.textContent = detail.error;
    } else {
      errorElement.hidden = true;
      errorElement.textContent = "";
    }
  };

  const cleanup = () => {
    window.removeEventListener("forge:boot-status", handleStatus);
    window.removeEventListener("beforeunload", cleanup);
  };

  window.addEventListener("forge:boot-status", handleStatus);
  window.addEventListener("beforeunload", cleanup);
})();
