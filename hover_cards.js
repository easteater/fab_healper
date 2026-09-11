// 全局搜索"添加到我的库"按钮并点击未点过的(去重)。
// 鼠标悬停到哪张卡, 该卡会生成这个按钮; 点过的用 WeakSet 记录, 不重复点。
// 仅用于一轮遍历点击, 不碰其它逻辑。
(() => {
  window.__fab = window.__fab || {};
  // 页面上所有产品卡片(外层 fabkit-Surface-root 容器)
  window.__fab.allCards = () => Array.from(document.querySelectorAll('[class*="fabkit-Surface-root"]'));
  // 页面上所有"添加到我的库"按钮(悬浮/overlay)
  window.__fab.allAddButtons = () => Array.from(document.querySelectorAll('[aria-label="添加到我的库"]'));
  // 已点过的按钮集合 (WeakSet, 避免重复点击)
  window.__fab.clickedButtons = new WeakSet();
  // 全局查找所有"添加到我的库"按钮, 点击未点过的, 返回点击数
  window.__fab.clickUnclickedAddButtons = () => {
    const btns = document.querySelectorAll('[aria-label="添加到我的库"]');
    let clicked = 0;
    btns.forEach((b) => {
      if (window.__fab.clickedButtons.has(b)) return;
      window.__fab.clickedButtons.add(b);
      b.click();
      clicked++;
    });
    return clicked;
  };
})();
