/**
 * API 封装 — 对应后端接口
 * Auth:  POST /auth/register, POST /auth/login
 * Books: GET/POST /books/, GET/PUT/DELETE /books/{id}
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
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (keyword) params.set("keyword", keyword);
    return request(`/books/?${params}`);
  },

  async getBook(id) {
    return request(`/books/${id}`);
  },

  async createBook(title, author) {
    return request("/books/", {
      method: "POST",
      json: { title, author },
    });
  },

  async updateBook(id, title, author) {
    return request(`/books/${id}`, {
      method: "PUT",
      json: { title, author },
    });
  },

  async deleteBook(id) {
    return request(`/books/${id}`, { method: "DELETE" });
  },

  // ---------- AI ----------
  async chat(question) {
    return request("/ai/chat", {
      method: "POST",
      json: { question },
    });
  },
};
