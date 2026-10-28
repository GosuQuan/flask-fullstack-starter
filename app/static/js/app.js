(function () {
  const btn = document.getElementById("helloBtn");
  const input = document.getElementById("nameInput");
  const result = document.getElementById("result");

  if (!btn || !result) return;

  btn.addEventListener("click", async () => {
    const name = (input && input.value.trim()) || "";
    const url = name
      ? `/api/hello?name=${encodeURIComponent(name)}`
      : "/api/hello";

    btn.disabled = true;
    result.textContent = "请求中…";

    try {
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || `HTTP ${res.status}`);
      }
      result.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      result.textContent = `请求失败: ${err.message || err}`;
    } finally {
      btn.disabled = false;
    }
  });
})();
