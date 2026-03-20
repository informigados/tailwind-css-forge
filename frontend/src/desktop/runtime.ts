export function isDesktopShell(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

function getPickerApiBaseUrl() {
  return window.location.port === "5173"
    ? "http://127.0.0.1:8000/api"
    : `${window.location.origin}/api`;
}

export async function pickDirectory(title: string): Promise<string | null> {
  if (isDesktopShell()) {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selection = await open({
      directory: true,
      multiple: false,
      title,
    });

    if (Array.isArray(selection)) {
      return selection[0] ?? null;
    }

    return selection;
  }

  const response = await fetch(`${getPickerApiBaseUrl()}/system/pick-directory`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error("directory-picker-failed");
  }
  const payload = (await response.json()) as { supported: boolean; path: string | null };
  if (!payload.supported) {
    return null;
  }
  return payload.path;
}
