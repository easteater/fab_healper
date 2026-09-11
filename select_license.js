// 独立的许可(免费档)选择逻辑,供 buy_first 在"半收费(有许可)"页调用。
// 只做一件事:点许可下拉 -> 等渲染 -> 找到"免费"档 -> 点击。不碰其他逻辑。
const __fab_delay = (ms) => new Promise((r) => setTimeout(r, ms));

(() => {
  window.__fab.selectFreeLicense = async () => {
    // 1. 点许可下拉按钮(aria-haspopup=true, 文本含"选择许可")
    const buttons = Array.from(document.querySelectorAll('button'));
    const dropdownBtn = buttons.find((b) =>
      b.matches('[aria-haspopup="true"]') && (b.textContent || '').includes('选择许可')
    );
    if (!dropdownBtn) {
      return { ok: true, selected: false, reason: 'no dropdown (非半收费或已选免费)' };
    }
    dropdownBtn.click();

    // 2. 点后才生成下拉列表,给它渲染时间
    await __fab_delay(500);

    // 3. 轮询找 ul.fabkit-Dropdown-list 及其"免费"档 li
    for (let attempt = 0; attempt < 15; attempt++) {
      const ul = document.querySelector('ul.fabkit-Dropdown-list');
      if (ul) {
        const options = Array.from(
          ul.querySelectorAll('li.fabkit-Select-option[role="option"]')
        );
        const free = options.find((li) => {
          const bold = li.querySelector('[class*="Text--bold"]');
          const text = bold ? bold.textContent : (li.textContent || '');
          return text.includes('免费');
        });
        if (free) {
          free.click();
          return {
            ok: true,
            selected: true,
            tier: '免费',
            value: free.getAttribute('data-value'),
          };
        }
      }
      await __fab_delay(200);
    }
    return { ok: false, reason: 'free tier option not found after wait' };
  };
})();
