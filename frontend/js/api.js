/**
 * API 封装 — 对应后端接口
 * Auth:  POST /auth/register, POST /auth/login
 * Books: GET/POST /books/, PUT/DELETE /books/{id}
 * AI:    POST /ai/chat
 */
const API_BASE = "";

const TokenStore = {
  KEY: "bookshelf_token",
  USER_KEY: "bookshelf_user",

  get() {
    return localStorage.getItem(this.KEY);
  },

  set(token, username) {
    localStorage.setItem(this.KEY, token);
    if (username) localStorage.setItem(this.USER_KEY, username);
  },

  getUser() {
    return localStorage.getItem(this.USER_KEY) || "";
  },

  clear() {
    localStorage.removeItem(this.KEY);
    localStorage.removeItem(this.USER_KEY);
  },
};

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = TokenStore.get();

  if (token && !options.skipAuth) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.json);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { msg: text };
    }
  }

  if (!res.ok) {
    const msg =
      (data && (data.msg || data.detail || data.message)) ||
      `请求失败 (${res.status})`;
    const err = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

const api = {
  // ---------- Auth ----------
  async register(username, password) {
    return request("/auth/register", {
      method: "POST",
      json: { username, password },
      skipAuth: true,
    });
  },

  /** OAuth2PasswordRequestForm: application/x-www-form-urlencoded */
  async login(username, password) {
    const body = new URLSearchParams({
      username,
      password,
    });
    const data = await request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
      skipAuth: true,
    });
    TokenStore.set(data.access_token, username);
    return data;
  },

  logout() {
    TokenStore.clear();
  },

  // ---------- Books ----------
  async listBooks({ page = 1, pageSize = 10, keyword = "" } = {}) {
    // 有关键词走模糊查询；否则走分页列表
    if (keyword) {
      const params = new URLSearchParams({ keyword });
      return request(`/books/like?${params}`);
    }
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    return request(`/books/?${params}`);
  },

  async createBook(title, author, quantity = 1) {
    return request("/books/", {
      method: "POST",
      json: { title, author, quantity },
    });
  },

  async updateBook(id, title, author, quantity) {
    return request(`/books/${id}`, {
      method: "PUT",
      json: { title, author, quantity },
    });
  },

  async deleteBook(id) {
    return request(`/books/${id}`, { method: "DELETE" });
  },

  // ---------- AI（SSE 流式）----------
  async chatStream(question, { onText, onError, onDone } = {}) {
    const headers = {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    };
    const token = TokenStore.get();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/ai/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({ question }),
    });

    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        msg = data.msg || data.detail || msg;
      } catch (_) {}
      throw new Error(msg);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const line = part.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        let payload;
        try {
          payload = JSON.parse(line.slice(6));
        } catch (_) {
          continue;
        }
        if (payload.error) {
          onError?.(payload.error);
          return;
        }
        if (payload.done) {
          onDone?.();
          return;
        }
        if (payload.text) onText?.(payload.text);
      }
    }
    onDone?.();
  },
};
