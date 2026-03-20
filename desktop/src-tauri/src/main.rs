use std::{
    env,
    net::TcpListener,
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use reqwest::blocking::Client;
use serde::Serialize;
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder, PredefinedMenuItem},
    AppHandle, Emitter, Manager, RunEvent, Url, WebviewWindow,
};

const DESKTOP_PORT: u16 = 8433;
const HEALTH_TIMEOUT: Duration = Duration::from_secs(75);
const MENU_OPEN_BROWSER: &str = "open-browser";
const MENU_RELOAD_WINDOW: &str = "reload-window";

#[derive(Default)]
struct BackendState {
    child: Option<Child>,
    app_url: Option<String>,
}

#[derive(Serialize)]
struct BootStatus<'a> {
    phase: &'a str,
    detail: &'a str,
    error: Option<&'a str>,
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(Mutex::new(BackendState::default()))
        .setup(|app| {
            let menu = build_menu(app.handle())?;
            app.set_menu(menu)?;
            start_backend(app.handle().clone());
            Ok(())
        })
        .on_menu_event(|app, event| match event.id().as_ref() {
            MENU_OPEN_BROWSER => {
                if let Err(error) = open_in_browser(app) {
                    let _ = publish_status(
                        app.get_webview_window("main"),
                        BootStatus {
                            phase: "Unable to open browser",
                            detail: "The desktop shell could not open the external browser.",
                            error: Some(&error),
                        },
                    );
                }
            }
            MENU_RELOAD_WINDOW => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.eval("window.location.reload()");
                }
            }
            _ => {}
        })
        .build(tauri::generate_context!())
        .expect("failed to build desktop shell")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                let state = app_handle.state::<Mutex<BackendState>>();
                stop_backend(&state);
            }
        });
}

fn build_menu(app: &AppHandle) -> tauri::Result<tauri::menu::Menu<tauri::Wry>> {
    let open_browser = MenuItemBuilder::with_id(MENU_OPEN_BROWSER, "Open in Browser").build(app)?;
    let reload_window = MenuItemBuilder::with_id(MENU_RELOAD_WINDOW, "Reload Window").build(app)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let quit = PredefinedMenuItem::quit(app, Some("Quit"))?;

    MenuBuilder::new(app)
        .items(&[&open_browser, &reload_window, &separator, &quit])
        .build()
}

fn start_backend(app: AppHandle) {
    let window = app.get_webview_window("main");
    thread::spawn(move || {
        let launch_result = launch_backend(&app, window.clone());
        if let Err(error) = launch_result {
            let _ = publish_status(
                window,
                BootStatus {
                    phase: "Desktop boot failed",
                    detail: "The native shell was unable to start the local Forge runtime.",
                    error: Some(&error),
                },
            );
        }
    });
}

fn launch_backend(app: &AppHandle, window: Option<WebviewWindow>) -> Result<(), String> {
    if port_in_use(DESKTOP_PORT) {
        return Err(format!(
            "Port {DESKTOP_PORT} is already in use. Close the conflicting service and start Forge again."
        ));
    }

    publish_status(
        window.clone(),
        BootStatus {
            phase: "Resolving runtime layout",
            detail: "Inspecting the current execution layout before starting the launcher.",
            error: None,
        },
    )?;

    let app_root = resolve_app_root().ok_or_else(|| {
        "Could not resolve the Forge application root for the desktop shell.".to_string()
    })?;
    let launcher_path = app_root.join("scripts").join("launch_forge.py");
    if !launcher_path.exists() {
        return Err(format!("Launcher not found at {}", launcher_path.display()));
    }

    let python_command = resolve_python_command();
    publish_status(
        window.clone(),
        BootStatus {
            phase: "Preparing backend runtime",
            detail: "Starting the Python launcher and waiting for the local backend.",
            error: None,
        },
    )?;

    let mut command = Command::new(&python_command.program);
    command.args(&python_command.args);
    command
        .arg(&launcher_path)
        .arg("--no-browser")
        .arg("--port")
        .arg(DESKTOP_PORT.to_string())
        .env("FORGE_APP_ROOT", &app_root)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    let working_directory = if app_root.join("backend").exists() {
        app_root.clone()
    } else {
        app_root
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| app_root.clone())
    };
    command.current_dir(working_directory);

    let child = command
        .spawn()
        .map_err(|error| format!("Failed to start launcher: {error}"))?;

    {
        let state = app.state::<Mutex<BackendState>>();
        let mut locked = state
            .lock()
            .map_err(|_| "Desktop backend state lock is poisoned.".to_string())?;
        locked.child = Some(child);
        locked.app_url = Some(format!("http://127.0.0.1:{DESKTOP_PORT}"));
    }

    wait_for_health(window.clone())?;

    let target_url = format!("http://127.0.0.1:{DESKTOP_PORT}");
    publish_status(
        window.clone(),
        BootStatus {
            phase: "Opening Forge workspace",
            detail: "The local backend is healthy. Switching the window to the Forge interface.",
            error: None,
        },
    )?;

    if let Some(window) = window {
        let url = Url::parse(&target_url).map_err(|error| format!("Invalid desktop URL: {error}"))?;
        window
            .navigate(url)
            .map_err(|error| format!("Failed to open Forge in the desktop window: {error}"))?;
    }

    Ok(())
}

fn wait_for_health(window: Option<WebviewWindow>) -> Result<(), String> {
    let health_url = format!("http://127.0.0.1:{DESKTOP_PORT}/api/health");
    let client = Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|error| format!("Failed to build HTTP client: {error}"))?;

    let deadline = Instant::now() + HEALTH_TIMEOUT;
    while Instant::now() < deadline {
        if let Ok(response) = client.get(&health_url).send() {
            if response.status().is_success() {
                return Ok(());
            }
        }

        let _ = publish_status(
            window.clone(),
            BootStatus {
                phase: "Waiting for local healthcheck",
                detail: "Forge is installing dependencies or warming up the backend.",
                error: None,
            },
        );
        thread::sleep(Duration::from_millis(1250));
    }

    Err("The local backend did not become healthy before the desktop timeout.".to_string())
}

fn publish_status(window: Option<WebviewWindow>, status: BootStatus<'_>) -> Result<(), String> {
    let window = match window {
        Some(window) => window,
        None => return Ok(()),
    };

    let payload = serde_json::to_string(&status)
        .map_err(|error| format!("Failed to serialize desktop boot status: {error}"))?;
    let script = format!(
        "window.dispatchEvent(new CustomEvent('forge:boot-status', {{ detail: {} }}));",
        payload
    );
    window
        .eval(&script)
        .map_err(|error| format!("Failed to publish desktop boot status: {error}"))?;
    let _ = window.emit("forge:boot-status", payload);
    Ok(())
}

fn open_in_browser(app: &AppHandle) -> Result<(), String> {
    let state = app.state::<Mutex<BackendState>>();
    let locked = state
        .lock()
        .map_err(|_| "Desktop backend state lock is poisoned.".to_string())?;
    let url = locked
        .app_url
        .as_deref()
        .unwrap_or("http://127.0.0.1:8433")
        .to_string();

    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = Command::new("cmd");
        command.args(["/C", "start", "", &url]);
        command
    };

    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = Command::new("open");
        command.arg(&url);
        command
    };

    #[cfg(all(unix, not(target_os = "macos")))]
    let mut command = {
        let mut command = Command::new("xdg-open");
        command.arg(&url);
        command
    };

    command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("Failed to open browser for {url}: {error}"))?;
    Ok(())
}

fn stop_backend(state: &Mutex<BackendState>) {
    let Ok(mut locked) = state.lock() else {
        return;
    };
    let Some(mut child) = locked.child.take() else {
        return;
    };

    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("taskkill")
            .args(["/PID", &child.id().to_string(), "/T", "/F"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = child.kill();
    }

    let _ = child.wait();
}

fn resolve_app_root() -> Option<PathBuf> {
    if let Some(override_root) = env::var_os("FORGE_APP_ROOT") {
        let path = PathBuf::from(override_root);
        if path.exists() {
            return Some(path);
        }
    }

    let executable = env::current_exe().ok()?;
    for ancestor in executable.ancestors() {
        let installed_root = ancestor.join("app");
        if installed_root.join("scripts").join("launch_forge.py").exists()
            && ancestor.join("installer-manifest.json").exists()
        {
            return Some(installed_root);
        }

        if ancestor.join("scripts").join("launch_forge.py").exists()
            && ancestor.join("backend").exists()
            && ancestor.join("frontend").exists()
        {
            return Some(ancestor.to_path_buf());
        }
    }

    None
}

fn port_in_use(port: u16) -> bool {
    TcpListener::bind(("127.0.0.1", port)).is_err()
}

struct PythonCommand {
    program: String,
    args: Vec<String>,
}

fn resolve_python_command() -> PythonCommand {
    #[cfg(target_os = "windows")]
    {
        PythonCommand {
            program: "py".to_string(),
            args: vec!["-3".to_string()],
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        PythonCommand {
            program: "python3".to_string(),
            args: Vec::new(),
        }
    }
}
