(() => {
  // 每个商品页(稳定类 fabkit-Surface-root)。每个卡片含一个 Surface-root。
  const cards = document.querySelectorAll('div.fabkit-Surface-root');
  let removed = 0;
  cards.forEach(card => {
    // 含"已保存在我的库中"=已购买/已入库
    if ((card.textContent || '').includes('已保存在我的库中')) {
      // 向上找到"只包含这一个 Surface-root"的最近 fabkit-Stack-root 祖先
      // (单个商品包装,而非含多个 Surface-root 的最上层容器)
      let el = card.parentElement;
      while (el) {
        if (el.classList && el.classList.contains('fabkit-Stack-root')) {
          if (el.querySelectorAll('.fabkit-Surface-root').length === 1) {
            el.remove();  // 这是单个商品包装,删它
            removed++;
            break;
          }
        }
        el = el.parentElement;
      }
    }
  });
  return { removed };
})()
