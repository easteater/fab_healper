// 步骤4(独立文件):点击"添加到我的库"完成下单,并检测是否出现"已保存在我的库中"。
// 完成后由 buy_first.py 停掉浏览器。不碰其他逻辑。
(() => {
  // 点击"添加到我的库"按钮(完成入库/下单)
  window.__fab.addToLibrary = () => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const btn = buttons.find((b) => (b.textContent || '').includes('添加到我的库'));
    if (btn) {
      btn.click();
      return { ok: true, action: '添加到我的库' };
    }
    return { ok: false, reason: 'no 添加到我的库 button' };
  };

  // 检测任务是否完成(页面出现"已保存在我的库中")
  window.__fab.isComplete = () => {
    return (document.body.textContent || '').includes('已保存在我的库中');
  };
})();
