(() => {
  const $ = (sel) => document.querySelector(sel);

  // ---------- DOM ----------
  const authView = $("#auth-view");
  const appView = $("#app-view");
  const authForm = $("#auth-form");
  const authTitle = $("#auth-title");
  const authHint = $("#auth-hint");
  const authSubmit = $("#auth-submit");
  const authToggle = $("#auth-toggle");
  const authSwitchText = $("#auth-switch-text");
  const authMsg = $("#auth-msg");
  const currentUser = $("#current-user");
  const logoutBtn = $("#logout-btn");

  const bookTbody = $("#book-tbody");
  const searchForm = $("#search-form");
  const keywordInput = $("#keyword");
  const prevPageBtn = $("#prev-page");
  const nextPageBtn = $("#next-page");
  const pageInfo = $("#page-info");
  const openCreateBtn = $("#open-create");

  const dialog = $("#book-dialog");
  const bookForm = $("#book-form");
  const dialogTitle = $("#dialog-title");
  const bookIdInput = $("#book-id");
  const bookTitleInput = $("#book-title");
  const bookAuthorInput = $("#book-author");
  const bookQuantityInput = $("#book-quantity");
  const bookMsg = $("#book-msg");
  const dialogCancel = $("#dialog-cancel");

  const chatForm = $("#chat-form");
  const chatInput = $("#chat-input");
  const chatMessages = $("#chat-messages");
  const chatSubmit = $("#chat-submit");
  const toastEl = $("#toast");

  // ---------- State ----------
  let isRegisterMode = false;
  let page = 1;
  const pageSize = 10;
  let total = 0;
  let keyword = "";
  let toastTimer = null;

  // ---------- Helpers ----------
  function showMsg(el, text, type = "error") {
    el.hidden = false;
    el.textContent = text;
    el.className = `form-msg ${type}`;
  }

  function hideMsg(el) {
    el.hidden = true;
    el.textContent = "";
  }

  function toast(text) {
    toastEl.textContent = text;
    toastEl.hidden = false;
    requestAnimationFrame(() => toastEl.classList.add("show"));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("show");
      setTimeout(() => {
        toastEl.hidden = true;
      }, 250);
    }, 2400);
  }

  function showAuth() {
    authView.hidden = false;
    appView.hidden = true;
  }

  function showApp() {
    authView.hidden = true;
    appView.hidden = false;
    currentUser.textContent = TokenStore.getUser()
      ? `@${TokenStore.getUser()}`
      : "";
    loadBooks();
  }

  function setAuthMode(register) {
    isRegisterMode = register;
    authTitle.textContent = register ? "注册" : "登录";
    authHint.textContent = register
      ? "创建账号后即可使用图书管理"
      : "登录后管理图书与 AI 推荐";
    authSubmit.textContent = register ? "注册" : "登录";
    authSwitchText.textContent = register ? "已有账号？" : "还没有账号？";
    authToggle.textContent = register ? "去登录" : "去注册";
    hideMsg(authMsg);
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ---------- Auth ----------
  authToggle.addEventListener("click", () => setAuthMode(!isRegisterMode));

  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideMsg(authMsg);
    const username = $("#auth-username").value.trim();
    const password = $("#auth-password").value;
    authSubmit.disabled = true;

    try {
      if (isRegisterMode) {
        await api.register(username, password);
        showMsg(authMsg, "注册成功，请登录", "ok");
        setAuthMode(false);
        $("#auth-password").value = "";
      } else {
        await api.login(username, password);
        showApp();
        toast("登录成功");
      }
    } catch (err) {
      showMsg(authMsg, err.message || "操作失败");
    } finally {
      authSubmit.disabled = false;
    }
  });

  logoutBtn.addEventListener("click", () => {
    api.logout();
    showAuth();
    toast("已退出登录");
  });

  // ---------- Tabs ----------
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      $(`#tab-${tab.dataset.tab}`).classList.add("active");
    });
  });

  // ---------- Books ----------
  async function loadBooks() {
    bookTbody.innerHTML =
      '<tr><td colspan="5" class="empty">加载中…</td></tr>';
    try {
      const res = await api.listBooks({ page, pageSize, keyword });
      const data = res.data || {};
      total = data.total || 0;
      const items = data.items || [];
      const totalPages = Math.max(1, Math.ceil(total / pageSize));

      pageInfo.textContent = `第 ${page} / ${totalPages} 页 · 共 ${total} 本`;
      prevPageBtn.disabled = page <= 1;
      nextPageBtn.disabled = page >= totalPages;

      if (!items.length) {
        bookTbody.innerHTML =
          '<tr><td colspan="5" class="empty">暂无图书，点击「添加图书」开始</td></tr>';
        return;
      }

      bookTbody.innerHTML = items
        .map(
          (b) => `
        <tr data-id="${b.id}">
          <td>${b.id}</td>
          <td>${escapeHtml(b.title)}</td>
          <td>${escapeHtml(b.author)}</td>
          <td>${b.quantity ?? 0}</td>
          <td>
            <div class="actions">
              <button type="button" class="btn btn-secondary btn-sm" data-action="edit"
                data-id="${b.id}" data-title="${escapeHtml(b.title)}" data-author="${escapeHtml(b.author)}"
                data-quantity="${b.quantity ?? 0}">编辑</button>
              <button type="button" class="btn btn-danger" data-action="delete" data-id="${b.id}">删除</button>
            </div>
          </td>
        </tr>`
        )
        .join("");
    } catch (err) {
      bookTbody.innerHTML = `<tr><td colspan="5" class="empty">${escapeHtml(err.message)}</td></tr>`;
      if (err.status === 401) {
        api.logout();
        showAuth();
      }
    }
  }

  searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    keyword = keywordInput.value.trim();
    page = 1;
    loadBooks();
  });

  prevPageBtn.addEventListener("click", () => {
    if (page > 1) {
      page -= 1;
      loadBooks();
    }
  });

  nextPageBtn.addEventListener("click", () => {
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (page < totalPages) {
      page += 1;
      loadBooks();
    }
  });

  bookTbody.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const id = Number(btn.dataset.id);

    if (btn.dataset.action === "edit") {
      openBookDialog({
        id,
        title: btn.dataset.title,
        author: btn.dataset.author,
        quantity: Number(btn.dataset.quantity || 0),
      });
    }

    if (btn.dataset.action === "delete") {
      if (!confirm(`确定删除图书 ID ${id}？`)) return;
      try {
        await api.deleteBook(id);
        toast("删除成功");
        if ((page - 1) * pageSize >= total - 1 && page > 1) page -= 1;
        loadBooks();
      } catch (err) {
        toast(err.message || "删除失败");
      }
    }
  });

  function openBookDialog(book = null) {
    hideMsg(bookMsg);
    if (book) {
      dialogTitle.textContent = "编辑图书";
      bookIdInput.value = book.id;
      bookTitleInput.value = book.title;
      bookAuthorInput.value = book.author;
      bookQuantityInput.value = book.quantity ?? 1;
    } else {
      dialogTitle.textContent = "添加图书";
      bookIdInput.value = "";
      bookTitleInput.value = "";
      bookAuthorInput.value = "";
      bookQuantityInput.value = 1;
    }
    dialog.showModal();
    bookTitleInput.focus();
  }

  openCreateBtn.addEventListener("click", () => openBookDialog());

  dialogCancel.addEventListener("click", () => dialog.close());

  bookForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideMsg(bookMsg);
    const id = bookIdInput.value;
    const title = bookTitleInput.value.trim();
    const author = bookAuthorInput.value.trim();
    const quantity = Number(bookQuantityInput.value);

    if (!Number.isInteger(quantity) || quantity < 0) {
      showMsg(bookMsg, "数量须为大于等于 0 的整数");
      return;
    }

    try {
      if (id) {
        await api.updateBook(Number(id), title, author, quantity);
        toast("更新成功");
      } else {
        await api.createBook(title, author, quantity);
        toast("添加成功");
        page = 1;
      }
      dialog.close();
      loadBooks();
    } catch (err) {
      showMsg(bookMsg, err.message || "保存失败");
    }
  });

  // ---------- AI Chat ----------
  function appendBubble(text, role) {
    const div = document.createElement("div");
    div.className = `chat-bubble ${role}`;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;

    appendBubble(question, "user");
    chatInput.value = "";
    chatSubmit.disabled = true;
    const loading = appendBubble("思考中…", "bot loading");

    try {
      const res = await api.chat(question);
      loading.remove();
      appendBubble(res.answer || "(无回复)", "bot");
    } catch (err) {
      loading.remove();
      appendBubble(`出错了：${err.message}`, "bot");
    } finally {
      chatSubmit.disabled = false;
      chatInput.focus();
    }
  });

  // ---------- Boot ----------
  if (TokenStore.get()) {
    showApp();
  } else {
    showAuth();
  }
})();
