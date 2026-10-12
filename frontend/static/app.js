const STATUSES = [
  ["todo", "To do"],
  ["in_progress", "In progress"],
  ["done", "Done"],
];
const FILTERS = [["", "All"], ...STATUSES];
let currentFilter = "";

const $ = (selector) => document.querySelector(selector);

// Build DOM nodes with textContent only, so user input is never parsed as HTML.
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node[key] = value;
  }
  node.append(...children);
  return node;
}

let toastTimer;
function toast(message) {
  const box = $("#toast");
  box.textContent = message;
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (box.hidden = true), 3500);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : data.detail?.[0]?.msg;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return data;
}

function renderFilters() {
  const box = $("#filters");
  box.replaceChildren(
    ...FILTERS.map(([value, label]) =>
      el(
        "button",
        {
          type: "button",
          class: value === currentFilter ? "active" : "",
          textContent: label,
          onclick: () => {
            currentFilter = value;
            renderFilters();
            loadTasks();
          },
        },
      ),
    ),
  );
}

function renderTask(task) {
  const select = el(
    "select",
    {
      "aria-label": "Status",
      onchange: (event) => updateTask(task.id, { status: event.target.value }),
    },
    ...STATUSES.map(([value, label]) =>
      el("option", { value, textContent: label, selected: value === task.status }),
    ),
  );
  const item = el(
    "li",
    { class: `task ${task.status}` },
    el("div", { class: "task-title", textContent: task.title }),
    el(
      "div",
      { class: "task-meta" },
      el("span", { class: `badge ${task.priority}`, textContent: task.priority }),
      select,
      el("button", {
        class: "icon-btn",
        title: "Delete task",
        textContent: "×",
        onclick: () => deleteTask(task.id),
      }),
    ),
  );
  if (task.description) item.append(el("div", { class: "task-desc", textContent: task.description }));
  return item;
}

async function loadTasks() {
  const query = currentFilter ? `?status=${encodeURIComponent(currentFilter)}` : "";
  try {
    const tasks = await api(`/api/tasks${query}`);
    const list = $("#task-list");
    if (!tasks.length) {
      list.replaceChildren(el("li", { class: "empty", textContent: "No tasks here yet." }));
    } else {
      list.replaceChildren(...tasks.map(renderTask));
    }
  } catch (error) {
    toast(`Could not load tasks: ${error.message}`);
  }
}

async function loadStats() {
  try {
    const data = await api("/api/stats");
    const cards = [
      ["Total", data.total],
      ["To do", data.by_status.todo],
      ["In progress", data.by_status.in_progress],
      ["Done", data.by_status.done],
    ];
    $("#stats").replaceChildren(
      ...cards.map(([label, value]) =>
        el("div", { class: "stat" }, el("div", { class: "num", textContent: value }), el("div", { class: "label", textContent: label })),
      ),
    );
  } catch {
    $("#stats").replaceChildren();
  }
}

async function loadReport() {
  const box = $("#report");
  try {
    const data = await api("/api/reports/summary");
    const row = (label, value) =>
      el("div", { class: "row" }, el("span", { textContent: label }), el("span", { textContent: value }));
    box.replaceChildren(
      row("Completion", `${data.completion_rate}%`),
      el("div", { class: "bar" }, el("div", { style: `width:${data.completion_rate}%` })),
      row("High priority", data.by_priority.high),
      row("Medium priority", data.by_priority.medium),
      row("Low priority", data.by_priority.low),
    );
  } catch {
    box.replaceChildren(el("div", { class: "empty", textContent: "Report service unavailable." }));
  }
}

async function loadActivity() {
  const list = $("#activity");
  try {
    const items = await api("/api/notifications");
    if (!items.length) {
      list.replaceChildren(el("li", { textContent: "Nothing yet." }));
      return;
    }
    list.replaceChildren(
      ...items.map((item) =>
        el(
          "li",
          {},
          item.message,
          el("time", { textContent: new Date(item.created_at).toLocaleTimeString() }),
        ),
      ),
    );
  } catch {
    list.replaceChildren(el("li", { textContent: "Notification service unavailable." }));
  }
}

async function loadServices() {
  try {
    const data = await api("/api/services");
    $("#services").replaceChildren(
      ...Object.entries(data).map(([name, state]) =>
        el("span", { class: `pill ${state}` }, el("span", { class: "dot" }), name),
      ),
    );
  } catch {
    $("#services").replaceChildren();
  }
}

async function updateTask(id, changes) {
  try {
    await api(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(changes) });
    refreshAll();
  } catch (error) {
    toast(error.message);
  }
}

async function deleteTask(id) {
  try {
    await api(`/api/tasks/${id}`, { method: "DELETE" });
    refreshAll();
  } catch (error) {
    toast(error.message);
  }
}

$("#task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const payload = {
    title: form.title.value.trim(),
    description: form.description.value.trim(),
    priority: form.priority.value,
  };
  try {
    await api("/api/tasks", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    refreshAll();
  } catch (error) {
    toast(error.message);
  }
});

function refreshAll() {
  // Notifications are written in the background, so give them a moment.
  loadTasks();
  loadStats();
  loadReport();
  setTimeout(loadActivity, 400);
}

renderFilters();
refreshAll();
loadServices();
setInterval(loadServices, 10000);
setInterval(() => { loadStats(); loadActivity(); }, 10000);
