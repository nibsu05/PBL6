"use strict";

window.PBL6Portal = (() => {
  const messages = {
    invalid_credentials: "Tên đăng nhập hoặc mật khẩu chưa đúng.",
    too_many_attempts: "Đã thử nhiều lần. Vui lòng thử lại sau một phút.",
    weak_password: "Mật khẩu cần ít nhất 12 ký tự.",
    invalid_username: "Tên phải dài 3–32 ký tự, có thể dùng chữ, số, dấu chấm, gạch ngang hoặc gạch dưới.",
    account_exists: "Tài khoản đã được tạo. Tải lại trang để đăng nhập.",
    source_check_recent: "Vừa kiểm tra nguồn. Vui lòng chờ khoảng 5 phút giữa hai lần kiểm tra.",
  };

  async function api(path, options) {
    const response = await fetch(path, options);
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(messages[data.error] || "Không thực hiện được yêu cầu. Vui lòng thử lại.");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  const send = (path, body = {}) => api(path, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  });

  async function bindAccount() {
    const form = document.getElementById("signin-form");
    const logout = document.getElementById("sign-out");
    if (!form && !logout) return;
    const message = document.getElementById("signin-message");
    try {
      const session = await api("/api/account");
      if (logout && session.username) {
        const name = document.getElementById("account-name");
        name.textContent = session.username;
        name.hidden = false;
        document.getElementById("account-link")?.setAttribute("hidden", "");
        logout.hidden = false;
        logout.addEventListener("click", async () => {
          logout.disabled = true;
          try {
            await send("/api/account/logout");
            window.location.replace("/");
          } catch {
            logout.disabled = false;
            logout.textContent = "Thử đăng xuất lại";
          }
        });
      }
      if (!form) return;
      const setup = session.setup_required;
      const name = form.elements.username;
      const password = form.elements.password;
      const confirm = document.getElementById("password-repeat");
      const submit = document.getElementById("signin-submit");
      if (setup) {
        document.getElementById("signin-title").textContent = "Tạo tài khoản";
        document.getElementById("signin-description").textContent = "Thiết lập lần đầu. Chọn mật khẩu riêng cho web, dài ít nhất 12 ký tự.";
        document.getElementById("confirm-password").hidden = false;
        confirm.required = true;
        password.minLength = 12;
        password.autocomplete = "new-password";
        submit.textContent = "Tạo tài khoản";
      }
      form.hidden = false;
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        message.hidden = true;
        if (setup && password.value !== confirm.value) {
          message.textContent = "Hai ô mật khẩu chưa khớp.";
          message.hidden = false;
          confirm.focus();
          return;
        }
        submit.disabled = true;
        try {
          await send(setup ? "/api/account/setup" : "/api/account/login",
                     {username: name.value, password: password.value});
          password.value = "";
          confirm.value = "";
          window.location.replace("/dashboard");
        } catch (error) {
          message.textContent = error.message;
          message.hidden = false;
          submit.disabled = false;
        }
      });
    } catch {
      if (message) {
        message.textContent = "Chưa đọc được trạng thái tài khoản. Hãy tải lại trang.";
        message.hidden = false;
      }
    }
  }

  bindAccount();
  return {api, send};
})();
